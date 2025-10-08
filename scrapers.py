"""
Scrapers complets avec support Tor pour l'extraction des données produit.
Chaque scraper s'appuie sur une session Tor avec gestion automatique des retries.
"""

from __future__ import annotations

import json
import re
import time
from typing import Dict, List, Optional

import requests
from bs4 import BeautifulSoup

from config import (
    MAX_RETRIES,
    REQUEST_TIMEOUT,
    RETRY_DELAY,
    TOR_CONTROL_HOST,
    TOR_CONTROL_PORT,
    TOR_CONTROL_PASSWORD,
    TOR_PROXY,
    TOR_RENEW_DELAY,
    TOR_USER_AGENT,
)


class TorSession:
    """Gestion des sessions HTTP via Tor."""

    @staticmethod
    def create_session() -> requests.Session:
        """Crée une session HTTP configurée pour Tor."""
        session = requests.Session()
        session.proxies = {
            "http": TOR_PROXY,
            "https": TOR_PROXY,
        }
        session.headers.update({
            "User-Agent": TOR_USER_AGENT,
            "Accept": (
                "text/html,application/xhtml+xml,application/xml;q=0.9,"
                "image/avif,image/webp,*/*;q=0.8"
            ),
            "Accept-Language": "fr-FR,fr;q=0.9,en-US;q=0.8,en;q=0.7",
            "Accept-Encoding": "gzip, deflate, br",
            "Cache-Control": "no-cache",
            "Pragma": "no-cache",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
        })
        # IMPORTANT: Activer la décompression automatique pour gzip/deflate/br
        # (équivalent de curl --compressed)
        # requests le fait normalement automatiquement, mais on force ici
        return session

    @staticmethod
    def renew_tor_identity() -> bool:
        """Renouvelle l'identité Tor via le port de contrôle."""
        try:
            import telnetlib

            with telnetlib.Telnet(TOR_CONTROL_HOST, TOR_CONTROL_PORT, timeout=5) as tn:
                if TOR_CONTROL_PASSWORD:
                    auth = f'AUTHENTICATE "{TOR_CONTROL_PASSWORD}"\r\n'.encode()
                else:
                    auth = b'AUTHENTICATE ""\r\n'
                tn.write(auth)
                if b"250 OK" not in tn.read_until(b"250", timeout=5):
                    return False
                tn.write(b"SIGNAL NEWNYM\r\n")
                if b"250 OK" not in tn.read_until(b"250", timeout=5):
                    return False

            time.sleep(TOR_RENEW_DELAY)
            print("   🔄 Identité Tor renouvelée")
            return True
        except Exception:
            print("   ⚠️  Impossible de renouveler l'identité Tor automatiquement")
            return False


class BaseScraper:
    """Classe de base partagée par les scrapers de chaque site."""

    def __init__(self) -> None:
        self.session: Optional[requests.Session] = None
        self.max_retries = MAX_RETRIES

    def _get_session(self) -> requests.Session:
        if self.session is None:
            self.session = TorSession.create_session()
        return self.session

    def _fetch_with_retry(self, url: str, max_retries: Optional[int] = None) -> requests.Response:
        """Récupère une page HTML avec gestion des erreurs et rotation Tor."""
        attempts = max_retries or self.max_retries

        for attempt in range(1, attempts + 1):
            try:
                response = self._get_session().get(url, timeout=REQUEST_TIMEOUT)
                if response.status_code == 403 and attempt < attempts:
                    print(f"   ⚠️  403 Forbidden (tentative {attempt}/{attempts})")
                    if TorSession.renew_tor_identity():
                        self.session = None
                    time.sleep(RETRY_DELAY)
                    continue

                response.raise_for_status()
                return response
            except requests.RequestException as exc:
                print(f"   ⚠️  Erreur réseau (tentative {attempt}/{attempts}): {exc}")
                if attempt == attempts:
                    raise
                if TorSession.renew_tor_identity():
                    self.session = None
                time.sleep(RETRY_DELAY)

        raise RuntimeError(f"Échec de récupération après {attempts} tentatives")

    @staticmethod
    def _clean_entities(text: Optional[str]) -> str:
        """Nettoie les entités HTML et normalise les espaces."""
        if not text:
            return ""

        replacements = {
            "&eacute;": "é",
            "&egrave;": "è",
            "&agrave;": "à",
            "&ugrave;": "ù",
            "&acirc;": "â",
            "&ocirc;": "ô",
            "&icirc;": "î",
            "&ecirc;": "ê",
            "&nbsp;": " ",
            "&#39;": "'",
            "&rsquo;": "'",
            "&amp;": "&",
            "&ccedil;": "ç",
            "\\u00e9": "é",
            "\\u00e8": "è",
            "\\u00e0": "à",
            "\\u00e7": "ç",
        }
        for old, new in replacements.items():
            text = text.replace(old, new)
        return re.sub(r"\s+", " ", text).strip()

    @staticmethod
    def _text_or_empty(element: Optional[BeautifulSoup]) -> str:
        """Retourne le texte nettoyé d'un élément BeautifulSoup."""
        if element is None:
            return ""
        return BaseScraper._clean_entities(element.get_text(separator=" ", strip=True))


class CocooncenterScraper(BaseScraper):
    """Scraper Cocooncenter - Basé sur le script bash qui fonctionne."""

    def extract(self, url: str, ean: str) -> Dict:
        product = {
            "site": "Cocooncenter",
            "ean": ean,
            "url": url,
            "avis_clients": [],
        }

        response = self._fetch_with_retry(url)
        html = response.text
        soup = BeautifulSoup(html, "html.parser")

        # 1. TITRE
        if soup.title:
            product["titre"] = self._clean_entities(soup.title.get_text())

        # 2. PRIX (depuis JSON-LD)
        price_match = re.search(r'"price":\s*"([^"]*)"', html)
        if price_match:
            product["prix"] = price_match.group(1) + "€"

        # 3. DESCRIPTION (itemprop="description" ou fallback)
        desc_elem = soup.find(itemprop="description")
        if desc_elem:
            p_tag = desc_elem.find("p")
            if p_tag:
                product["description"] = self._text_or_empty(p_tag)

        if not product.get("description"):
            desc_div = soup.find("div", id="type_info_prio_11_1")
            if desc_div:
                p_tag = desc_div.find("p")
                if p_tag:
                    product["description"] = self._text_or_empty(p_tag)

        # 4. CODE EAN
        ean_elem = soup.find("span", itemprop="gtin13")
        if ean_elem:
            product["ean_verif"] = self._text_or_empty(ean_elem)

        # 5. CONTENANCE (recherche dans les td)
        contenance_match = re.search(r'<td[^>]*>([^<]*\d+\s*(?:ml|mL|ML|cl|CL)[^<]*)</td>', html, re.IGNORECASE)
        if contenance_match:
            product["contenance"] = self._clean_entities(contenance_match.group(1))

        # 6. FORME
        forme_match = re.search(r'<td[^>]*>([^<]*(?:Crème|Gel|Lotion|Spray|Tube|Flacon|Huile|Sérum)[^<]*)</td>', html, re.IGNORECASE)
        if forme_match:
            product["forme"] = self._clean_entities(forme_match.group(1))

        # 7. NOTE GÉNÉRALE
        note_match = re.search(r'class="bvseo-ratingValue"[^>]*>([0-9.]+)', html)
        if note_match:
            product["note"] = note_match.group(1) + "/5"

        nb_avis_match = re.search(r'class="bvseo-reviewCount"[^>]*>(\d+)', html)
        if nb_avis_match:
            product["nb_avis"] = nb_avis_match.group(1)

        # 8. COMPOSITION
        comp_div = soup.find("div", class_="longcompo")
        if comp_div:
            p_tag = comp_div.find("p")
            if p_tag:
                product["composition"] = self._text_or_empty(p_tag)

        # 9. CONSEILS D'UTILISATION
        conseils_div = soup.find("div", id="type_info_prio_6_1")
        if conseils_div:
            p_tag = conseils_div.find("p")
            if p_tag:
                product["conseils"] = self._text_or_empty(p_tag)

        # 10. AVIS CLIENTS (extraction depuis bvseo-reviewsSection)
        product["avis_clients"] = self._extract_cocooncenter_reviews(soup, html)

        return product

    def _extract_cocooncenter_reviews(self, soup: BeautifulSoup, html: str) -> List[Dict]:
        """Extrait les avis depuis bvseo-reviewsSection (méthode bash)."""
        reviews: List[Dict] = []

        # Chercher la section des avis
        reviews_section = soup.find("div", id="bvseo-reviewsSection")
        if not reviews_section:
            return reviews

        # Trouver tous les avis (class="bvseo-review")
        review_divs = reviews_section.find_all("div", class_="bvseo-review")

        for review_div in review_divs[:5]:  # Top 5 avis
            review_data = {}

            # Note (itemprop="ratingValue")
            rating_span = review_div.find("span", itemprop="ratingValue")
            if rating_span:
                review_data["note"] = self._text_or_empty(rating_span)

            # Auteur et titre (deux spans itemprop="name")
            name_spans = review_div.find_all("span", itemprop="name")
            if len(name_spans) >= 2:
                # Premier = auteur, deuxième = titre
                review_data["auteur"] = self._text_or_empty(name_spans[0])
                review_data["titre"] = self._text_or_empty(name_spans[1])
            elif len(name_spans) == 1:
                review_data["auteur"] = self._text_or_empty(name_spans[0])

            # Texte de l'avis (itemprop="description")
            desc_span = review_div.find("span", itemprop="description")
            if desc_span:
                review_data["avis"] = self._text_or_empty(desc_span)

            if review_data.get("auteur") and review_data.get("avis"):
                reviews.append(review_data)

        return reviews

    def _extract_reviews_from_jsonld(self, soup: BeautifulSoup) -> List[Dict]:
        """Extrait les avis clients depuis les blocs JSON-LD."""
        reviews: List[Dict] = []

        def collect(obj: object) -> None:
            if isinstance(obj, dict):
                if obj.get("@type") == "Review":
                    reviews.append(obj)
                for value in obj.values():
                    collect(value)
            elif isinstance(obj, list):
                for item in obj:
                    collect(item)

        for script in soup.find_all("script", type="application/ld+json"):
            content = (script.string or "").strip()
            if not content:
                continue
            try:
                data = json.loads(content)
            except json.JSONDecodeError:
                continue
            collect(data)

        formatted_reviews: List[Dict] = []
        for review in reviews[:5]:
            author = review.get("author")
            if isinstance(author, dict):
                author = author.get("name")

            formatted_reviews.append({
                "auteur": self._clean_entities(author or "Anonyme"),
                "avis": self._clean_entities(review.get("reviewBody", "")),
                "note": f"{review.get('reviewRating', {}).get('ratingValue', 'N/A')}/5"
                if isinstance(review.get("reviewRating"), dict)
                else self._clean_entities(str(review.get("reviewRating", ""))),
                "date": review.get("datePublished"),
            })

        return formatted_reviews


class PharmaGDDScraper(BaseScraper):
    """Scraper Pharma-GDD (anti-403 avec retries)."""

    def extract(self, url: str, ean: str) -> Dict:
        product = {
            "site": "Pharma-GDD",
            "ean": ean,
            "url": url,
            "avis_clients": [],
        }

        response = self._fetch_with_retry(url, max_retries=MAX_RETRIES + 2)
        html = response.text
        soup = BeautifulSoup(html, "html.parser")

        json_fields = {
            "titre": r'"name":"([^"]*)"',
            "description": r'"description":"([^"]*)"',
            "note": r'"ratingValue":([0-9.]+)',
            "nb_avis": r'"reviewCount":([0-9]+)',
        }
        for key, pattern in json_fields.items():
            match = re.search(pattern, html)
            if match:
                value = self._clean_entities(match.group(1))
                if key == "note":
                    value = f"{value}/5"
                product[key] = value

        price_match = re.search(r'<span data-js-product-price[^>]*>([^<]*)', html)
        if price_match:
            product["prix"] = self._clean_entities(price_match.group(1))

        ean_match = re.search(r'<span data-js-product-reference[^>]*>([^<]*)', html)
        if ean_match:
            product["ean_verif"] = self._clean_entities(ean_match.group(1))

        custom_match = re.search(r'<span data-js-custom-code[^>]*>([^<]*)', html)
        if custom_match:
            product["code_custom"] = self._clean_entities(custom_match.group(1))

        brand_match = re.search(r'<a class="brand"[^>]*title="[^"]*"[^>]*>([^<]*)', html)
        if brand_match:
            product["marque"] = self._clean_entities(brand_match.group(1))

        comp_div = soup.find("div", id="Composition")
        if comp_div:
            product["composition"] = self._text_or_empty(comp_div.find("div", class_="text"))

        conseils_div = soup.find("div", id="usages")
        if conseils_div:
            product["conseils"] = self._text_or_empty(conseils_div.find("div", class_="text"))

        product["avis_clients"] = self._extract_flipcard_reviews(soup)
        return product

    def _extract_flipcard_reviews(self, soup: BeautifulSoup) -> List[Dict]:
        reviews: List[Dict] = []
        for card in soup.find_all("div", class_="flip-card", limit=10):
            texte = card.find("p")
            if not texte:
                continue

            stars = len(card.find_all("i", {"data-icon": "star"}))
            date = card.find("div", class_="date")
            auteur_match = re.search(r"par\s+([^\n\r]+)", card.get_text())

            reviews.append({
                "avis": self._text_or_empty(texte),
                "note": f"{stars}/5" if stars else "N/A",
                "date": self._clean_entities(date.get_text(strip=True) if date else ""),
                "auteur": self._clean_entities(auteur_match.group(1)) if auteur_match else "Anonyme",
            })

        return reviews


class DrakkarsScraper(BaseScraper):
    """Scraper Pharmacie des Drakkars (extraction complète)."""

    def extract(self, url: str, ean: str) -> Dict:
        product = {
            "site": "Pharmacie des Drakkars",
            "ean": ean,
            "url": url,
            "avis_clients": [],
        }

        response = self._fetch_with_retry(url)
        html = response.text
        soup = BeautifulSoup(html, "html.parser")

        if soup.title:
            product["titre"] = self._clean_entities(soup.title.get_text())

        price_match = re.search(r'class="pdt-detail-price[^>]*><strong>([0-9,]+)', html)
        if price_match:
            product["prix"] = price_match.group(1) + "€"

        ref_elem = soup.find(id="product_reference")
        if ref_elem:
            product["reference"] = self._text_or_empty(ref_elem)

        variantes = {
            self._clean_entities(a.get("title", ""))
            for a in soup.select('a[title*="mL"], a[title*="ml"], a[title*="ML"]')
            if a.get("title")
        }
        if variantes:
            product["variantes"] = " | ".join(sorted(variantes))

        desc_article = soup.find("article", class_="desc-longue")
        if desc_article:
            product["description"] = self._text_or_empty(desc_article)

        comp_div = soup.find("div", id="upcomposition")
        if comp_div:
            product["composition"] = self._text_or_empty(comp_div)

        note_match = re.search(r'<span class="text-bold">([0-9]/[0-9])</span>', html)
        if note_match:
            product["note"] = note_match.group(1)

        avis_match = re.search(
            r'<span class="text-bold">[0-9]/[0-9]</span>\s*\|\s*<span>([0-9]+)',
            html,
        )
        if avis_match:
            product["nb_avis"] = avis_match.group(1)

        pourcentage_match = re.search(
            r'class="fa-4x text-bold has-color-theme">([0-9]+%)',
            html,
        )
        if pourcentage_match:
            product["pourcentage_reco"] = pourcentage_match.group(1)

        product["avis_clients"] = self._extract_drakkars_reviews(html, soup)

        conseils_section = soup.find(string=re.compile(r"Avis du pharmacien", re.IGNORECASE))
        if conseils_section:
            paragraph = conseils_section.find_parent().find_next("p")
            if paragraph:
                product["conseils_pharmacien"] = self._text_or_empty(paragraph)

        return product

    def _extract_drakkars_reviews(self, html: str, soup: BeautifulSoup) -> List[Dict]:
        """Extraire un avis client principal depuis le JSON ou le HTML."""
        reviews: List[Dict] = []

        json_match = re.search(r'"review"\s*:\s*\{([^}]+)\}', html)
        if json_match:
            json_section = json_match.group(0)

            auteur_match = re.search(r'"name":\s*"([^"]*)"', json_section)
            avis_match = re.search(r'"reviewBody":\s*"([^"]*)"', json_section)
            note_match = re.search(r'"ratingValue":\s*([0-9]+)', json_section)

            review = {
                "auteur": self._clean_entities(auteur_match.group(1)) if auteur_match else "Anonyme",
                "avis": self._clean_entities(avis_match.group(1)) if avis_match else "",
                "note": f"{note_match.group(1)}/5" if note_match else "N/A",
            }

            date_match = re.search(r'class="gris-clair">\s*([0-9.]+)', html)
            if date_match:
                review["date"] = date_match.group(1)

            if review["avis"]:
                reviews.append(review)

        if reviews:
            return reviews

        # Fallback: essayer de récupérer via la section HTML des avis
        avis_section = soup.find("div", id="avis")
        if avis_section:
            first_review = avis_section.find("div", class_="avis")
            if first_review:
                reviews.append({
                    "auteur": self._text_or_empty(first_review.find("span", class_="auteur")),
                    "avis": self._text_or_empty(first_review.find("p")),
                    "note": self._text_or_empty(first_review.find("span", class_="note")),
                })

        return reviews
