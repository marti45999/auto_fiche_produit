import re
import time
from typing import Optional, Tuple

import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.firefox.service import Service
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from config import DEFAULT_USER_AGENT, SEARCH_TIMEOUT, TOR_PROXY


"""
Modules de recherche rapide par EAN.
Les recherches ne passent pas par Tor afin de réduire la latence.
"""


class BaseSearcher:
    """Classe de base pour les modules de recherche."""

    def __init__(self) -> None:
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": DEFAULT_USER_AGENT,
            "Accept-Language": "fr-FR,fr;q=0.9,en-US;q=0.8,en;q=0.7",
        })


class CocooncenterSearcher(BaseSearcher):
    """Recherche produits sur Cocooncenter."""

    def search(self, ean: str) -> Tuple[bool, Optional[str]]:
        """Recherche par EAN sur Cocooncenter."""
        url = "https://www.cocooncenter.com/index/search/searchVue"
        headers = {
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
            "X-Requested-With": "XMLHttpRequest"
        }
        data = {"recherche": ean}

        try:
            response = self.session.post(
                url, headers=headers, data=data, timeout=SEARCH_TIMEOUT
            )
            response.raise_for_status()
            payload = response.json()

            if payload.get("nb_total", 0) > 0:
                urls = re.findall(r'href="(/[^"]+\.html)"', payload.get("vue", ""))
                product_urls = [u for u in urls if not u.startswith("/c/")]
                if product_urls:
                    return True, "https://www.cocooncenter.com" + product_urls[0]
            return False, None
        except Exception as exc:  # noqa: BLE001
            print(f"   ⚠️  Erreur Cocooncenter: {exc}")
            return False, None


class PharmaGDDSearcher(BaseSearcher):
    """Recherche produits sur Pharma-GDD."""

    def search(self, ean: str) -> Tuple[bool, Optional[str], Optional[str]]:
        """Recherche par EAN sur Pharma-GDD."""
        url = f"https://www.pharma-gdd.com/fr/search/autocomplete?s={ean}"
        headers = {"X-Requested-With": "XMLHttpRequest"}

        try:
            response = self.session.get(url, headers=headers, timeout=SEARCH_TIMEOUT)
            response.raise_for_status()
            data = response.json()

            if data.get("length", 0) > 0:
                key, val = next(
                    ((key, value) for key, value in data.items() if key.startswith("variant_")),
                    (None, None),
                )
                if val:
                    product_url = "https://www.pharma-gdd.com" + val["href"]
                    return True, product_url, val.get("label")
            return False, None, None
        except Exception as exc:  # noqa: BLE001
            print(f"   ⚠️  Erreur Pharma-GDD: {exc}")
            return False, None, None


class DrakkarsSearcher:
    """Recherche produits sur Pharmacie des Drakkars via Selenium + Tor."""

    BASE_URL = "https://www.pharmaciedesdrakkars.com"
    # fallback layer hash (observé côté site). Si un jour il change, on garde le chemin "input" qui n'en dépend pas.
    LAYER_HASH_PREFIX = "#6a37/fullscreen/m=and&q="

    def __init__(self) -> None:
        """Initialise le searcher (le driver sera créé à la demande)."""
        self.driver = None

    def _create_driver(self) -> webdriver.Firefox:
        """Crée un driver Firefox configuré avec Tor."""
        options = Options()
        options.add_argument("--headless")
        options.add_argument("--width=1400")
        options.add_argument("--height=1800")

        # Proxy Tor (SOCKS5) + DNS distant
        options.set_preference("network.proxy.type", 1)
        options.set_preference("network.proxy.socks", "127.0.0.1")
        options.set_preference("network.proxy.socks_port", 9050)
        options.set_preference("network.proxy.socks_version", 5)
        options.set_preference("network.proxy.socks_remote_dns", True)

        # UA + langues (réduit les frictions côté front/CDN)
        options.set_preference("general.useragent.override", DEFAULT_USER_AGENT)
        options.set_preference("intl.accept_languages", "fr-FR,fr;q=0.9,en-US;q=0.8,en;q=0.7")

        # Moins “automatisé”
        options.set_preference("dom.webdriver.enabled", False)
        options.set_preference("useAutomationExtension", False)

        # Si tu as geckodriver dans un chemin spécifique, active la ligne suivante:
        # service = Service("/usr/local/bin/geckodriver")
        # return webdriver.Firefox(service=service, options=options)
        return webdriver.Firefox(options=options)

    def _close_cookies_if_any(self, driver: webdriver.Firefox) -> None:
        """Ferme un éventuel bandeau cookies s'il est présent (best-effort)."""
        try:
            WebDriverWait(driver, 6).until(
                EC.element_to_be_clickable((
                    By.CSS_SELECTOR,
                    "button[aria-label*='Accepter'], .didomi-accept-button, "
                    ".cm-btn-accept, .tarteaucitronCTAButton, .cm-btn"
                ))
            ).click()
        except Exception:
            pass  # pas de popin détectée

    def _collect_product_url(self, driver: webdriver.Firefox) -> Optional[str]:
        """Récupère la première URL produit depuis le layer Doofinder."""
        wait = WebDriverWait(driver, 30)

        # attendre le conteneur résultats
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, ".dfd-results")))

        # 1) liens cliquables <a.dfd-card-link href="...">
        links = driver.find_elements(By.CSS_SELECTOR, ".dfd-results a.dfd-card-link[href]")
        urls = []
        for a in links:
            href = a.get_attribute("href") or ""
            if href and not href.startswith(f"{self.BASE_URL}/c/"):
                urls.append(href)

        # 2) fallback: attribut dfd-value-link sur la carte
        if not urls:
            cards = driver.find_elements(By.CSS_SELECTOR, ".dfd-results .dfd-card[dfd-value-link]")
            for c in cards:
                v = c.get_attribute("dfd-value-link") or ""
                if v and not v.startswith(f"{self.BASE_URL}/c/"):
                    urls.append(v)

        if urls:
            # Nettoie les paramètres (ex: ?mcs=...)
            return urls[0].split("?")[0]
        return None

    def search(self, ean: str) -> Tuple[bool, Optional[str]]:
        """Recherche par EAN sur Pharmacie des Drakkars via interface web (Tor)."""
        driver = None
        try:
            driver = self._create_driver()
            wait = WebDriverWait(driver, 40)

            # 1) ouvrir la home
            driver.get(self.BASE_URL)
            self._close_cookies_if_any(driver)

            # 2) chemin “input” (init du layer + saisie EAN)
            try:
                # clic déclencheur
                trigger = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "#form-search-keywords")))
                driver.execute_script("arguments[0].scrollIntoView({block:'center'});", trigger)
                trigger.click()

                # attendre que Doofinder soit monté
                wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "[class^='dfd-'], .dfd-searchbox")))

                # saisir l'EAN + ENTER
                input_box = wait.until(
                    EC.visibility_of_element_located(
                        (By.CSS_SELECTOR, "form.dfd-searchbox input.dfd-searchbox-input")
                    )
                )
                input_box.clear()
                input_box.send_keys(ean)
                from selenium.webdriver.common.keys import Keys  # import local pour éviter de casser tes imports
                input_box.send_keys(Keys.ENTER)

                # récupérer la première URL produit
                product_url = self._collect_product_url(driver)
                if product_url:
                    return True, product_url
            except Exception:
                # on tente le fallback hash si le chemin “input” échoue
                pass

            # 3) fallback “hash layer” (ouvre directement le layer fullscreen avec la requête)
            try:
                layer_url = f"{self.BASE_URL}/{self.LAYER_HASH_PREFIX}{ean}"
                driver.get(layer_url)
                self._close_cookies_if_any(driver)  # au cas où
                product_url = self._collect_product_url(driver)
                if product_url:
                    return True, product_url
            except Exception:
                pass

            # rien trouvé
            return False, None

        except Exception as exc:  # noqa: BLE001
            print(f"   ⚠️  Erreur Drakkars: {exc}")
            return False, None
        finally:
            if driver:
                driver.quit()

