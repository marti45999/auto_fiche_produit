#!/usr/bin/env python3
"""
Scraper Multi-Pharmacies - Point d'entrée principal
Recherche les produits par EAN et orchestre les scrapers spécifiques.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Dict, List

from searchers import CocooncenterSearcher, DrakkarsSearcher, PharmaGDDSearcher
from scrapers import CocooncenterScraper, DrakkarsScraper, PharmaGDDScraper


@dataclass
class SearchResult:
    """Résultat de recherche d'un site."""

    site: str
    found: bool
    url: str = ""
    label: str = ""


class MasterScraper:
    """Orchestrateur principal des recherches et extractions."""

    def __init__(self) -> None:
        # Phase de recherche rapide (sans Tor)
        self.searchers = {
            "cocooncenter": CocooncenterSearcher(),
            "pharmagdd": PharmaGDDSearcher(),
            "drakkars": DrakkarsSearcher(),
        }

        # Phase d'extraction complète (via Tor)
        self.scrapers = {
            "cocooncenter": CocooncenterScraper(),
            "pharmagdd": PharmaGDDScraper(),
            "drakkars": DrakkarsScraper(),
        }

    def search_all_sites(self, ean: str) -> Dict[str, SearchResult]:
        """Recherche le produit sur l'ensemble des sites supportés."""
        print(f"\n{'=' * 70}")
        print(f"🔎 PHASE 1 : RECHERCHE DU PRODUIT - EAN: {ean}")
        print(f"{'=' * 70}\n")

        results: Dict[str, SearchResult] = {}

        # Cocooncenter
        print("🔍 Recherche sur Cocooncenter...")
        found, url = self.searchers["cocooncenter"].search(ean)
        results["cocooncenter"] = SearchResult(
            site="Cocooncenter",
            found=found,
            url=url or "",
        )
        print(f"   {'✅ Trouvé' if found else '❌ Non trouvé'}\n")

        # Pharma-GDD
        print("🔍 Recherche sur Pharma-GDD...")
        found, url, label = self.searchers["pharmagdd"].search(ean)
        results["pharmagdd"] = SearchResult(
            site="Pharma-GDD",
            found=found,
            url=url or "",
            label=label or "",
        )
        print(f"   {'✅ Trouvé: ' + label if found else '❌ Non trouvé'}\n")

        # Pharmacie des Drakkars
        print("🔍 Recherche sur Pharmacie des Drakkars...")
        found, url = self.searchers["drakkars"].search(ean)
        results["drakkars"] = SearchResult(
            site="Pharmacie des Drakkars",
            found=found,
            url=url or "",
        )
        print(f"   {'✅ Trouvé' if found else '❌ Non trouvé'}\n")

        return results

    def extract_products(
        self, ean: str, search_results: Dict[str, SearchResult]
    ) -> Dict[str, Dict]:
        """Extrait les informations complètes pour chaque site où le produit est trouvé."""
        print(f"\n{'=' * 70}")
        print("📦 PHASE 2 : EXTRACTION DES DONNÉES (via Tor)")
        print(f"{'=' * 70}\n")

        found_sites = [key for key, result in search_results.items() if result.found]

        if not found_sites:
            print("❌ Aucun produit trouvé sur les sites\n")
            return {}

        found_names = ", ".join(search_results[key].site for key in found_sites)
        print(f"✅ Produit trouvé sur {len(found_sites)} site(s): {found_names}\n")

        products: Dict[str, Dict] = {}
        extraction_count = 0
        extraction_errors = 0

        for idx, site_key in enumerate(found_sites, 1):
            result = search_results[site_key]
            print(f"{'─' * 70}")
            print(f"🏪 [{idx}/{len(found_sites)}] Extraction depuis {result.site}...")
            print(f"🔗 URL: {result.url}")
            print(f"{'─' * 70}")

            try:
                print(f"🚀 Début de l'extraction pour {site_key}...")
                product_data = self.scrapers[site_key].extract(result.url, ean)

                if product_data:
                    products[site_key] = product_data
                    extraction_count += 1
                    print(f"✅ Extraction réussie pour {result.site}")
                    print(f"📦 Données extraites: Titre='{product_data.get('titre', 'N/A')}', Prix={product_data.get('prix', 'N/A')}")
                else:
                    print(f"⚠️  Extraction a retourné des données vides pour {result.site}")
                    extraction_errors += 1

                print()
            except ValueError as exc:  # EAN validation error
                extraction_errors += 1
                print(f"❌ ERREUR DE VALIDATION: {exc}")
                print(f"   Site: {result.site}")
                print(f"   EAN: {ean}\n")
            except Exception as exc:  # noqa: BLE001
                extraction_errors += 1
                print(f"❌ ERREUR LORS DE L'EXTRACTION: {type(exc).__name__}")
                print(f"   Site: {result.site}")
                print(f"   Message: {str(exc)}")
                import traceback
                print(f"   Traceback:")
                traceback.print_exc()
                print()

        print(f"{'=' * 70}")
        print(f"📊 BILAN EXTRACTION:")
        print(f"   ✅ Succès: {extraction_count}/{len(found_sites)}")
        print(f"   ❌ Erreurs: {extraction_errors}/{len(found_sites)}")
        print(f"{'=' * 70}\n")

        return products

    def display_results(self, products: Dict[str, Dict], ean: str) -> None:
        """Affiche les informations extraites et les sauvegarde en JSON."""
        print(f"\n{'=' * 70}")
        print("📊 RÉSULTATS FINAUX")
        print(f"{'=' * 70}\n")

        if not products:
            print("❌ Aucune donnée extraite\n")
            return

        for _, product in products.items():
            print(f"{'─' * 70}")
            print(f"🏪 {product.get('site', 'Site inconnu')}")
            print(f"{'─' * 70}")
            print(f"📦 Titre       : {product.get('titre', 'N/A')}")
            print(f"💰 Prix        : {product.get('prix', 'N/A')}")
            if product.get("marque"):
                print(f"🏢 Marque      : {product['marque']}")
            if product.get("reference"):
                print(f"🏷️  Référence   : {product['reference']}")
            if product.get("ean_verif"):
                print(f"🔢 EAN         : {product['ean_verif']}")
            if product.get("note"):
                avis = product.get("nb_avis", "0")
                print(f"⭐ Note        : {product['note']} ({avis} avis)")
            if product.get("pourcentage_reco"):
                print(f"🎯 Recommandé : {product['pourcentage_reco']}")
            print(f"🔗 URL         : {product.get('url', 'N/A')}")
            if description := product.get("description"):
                short = description[:150] + "..." if len(description) > 150 else description
                print(f"📝 Description : {short}")
            if composition := product.get("composition"):
                short = composition[:150] + "..." if len(composition) > 150 else composition
                print(f"🧪 Composition : {short}")
            if conseils := product.get("conseils"):
                print(f"💡 Conseils    : {conseils}")
            if conseils_pharmacien := product.get("conseils_pharmacien"):
                print(f"👨‍⚕️ Pharmacien : {conseils_pharmacien}")
            if avis_clients := product.get("avis_clients"):
                print(f"💬 Avis clients ({len(avis_clients)}) :")
                for avis in avis_clients[:3]:
                    auteur = avis.get("auteur", "Anonyme")
                    note = avis.get("note", "N/A")
                    texte = avis.get("avis", "")
                    short = texte[:120] + "..." if len(texte) > 120 else texte
                    print(f"   - {auteur} ({note}) : {short}")
            print()

        json_file = f"product_{ean}.json"
        with open(json_file, "w", encoding="utf-8") as handle:
            json.dump(products, handle, ensure_ascii=False, indent=2)

        print(f"💾 Résultats sauvegardés dans: {json_file}\n")

    def process_ean(self, ean: str) -> None:
        """Traite un code EAN complet."""
        search_results = self.search_all_sites(ean)
        products = self.extract_products(ean, search_results)
        self.display_results(products, ean)

    def process_multiple_eans(self, eans: List[str]) -> None:
        """Traite plusieurs codes EAN."""
        print(f"╔{'═' * 68}╗")
        print(f"║{'  SCRAPER MULTI-PHARMACIES - Traitement par lot':^68}║")
        print(f"╚{'═' * 68}╝")

        for index, ean in enumerate(eans, start=1):
            print(f"\n\n{'#' * 70}")
            print(f"# TRAITEMENT {index}/{len(eans)}")
            print(f"{'#' * 70}")
            self.process_ean(ean)

        print(f"\n{'=' * 70}")
        print(f"✨ TRAITEMENT TERMINÉ - {len(eans)} produit(s) traité(s)")
        print(f"{'=' * 70}\n")


def main() -> None:
    """Point d'entrée CLI."""
    print(f"╔{'═' * 68}╗")
    print(f"║{'  SCRAPER MULTI-PHARMACIES - Recherche par EAN':^68}║")
    print(f"╚{'═' * 68}╝\n")

    print("Mode de saisie:")
    print("1. Un seul code EAN")
    print("2. Plusieurs codes EAN (séparés par des virgules)")
    print("3. Charger depuis un fichier (eans.txt)\n")

    choice = input("Votre choix (1/2/3): ").strip()
    scraper = MasterScraper()

    if choice == "1":
        ean = input("\n🔢 Entrez le code EAN: ").strip()
        if ean:
            scraper.process_ean(ean)
        else:
            print("❌ Code EAN vide")
    elif choice == "2":
        eans_input = input(
            "\n🔢 Entrez les codes EAN (séparés par des virgules): "
        ).strip()
        eans = [ean.strip() for ean in eans_input.split(",") if ean.strip()]
        if eans:
            scraper.process_multiple_eans(eans)
        else:
            print("❌ Aucun code EAN valide")
    elif choice == "3":
        try:
            with open("eans.txt", "r", encoding="utf-8") as handle:
                eans = [line.strip() for line in handle if line.strip() and not line.startswith("#")]
            if eans:
                print(f"\n✅ {len(eans)} code(s) EAN chargé(s) depuis eans.txt")
                scraper.process_multiple_eans(eans)
            else:
                print("❌ Fichier vide")
        except FileNotFoundError:
            print("❌ Fichier eans.txt non trouvé")
    else:
        print("❌ Choix invalide")


if __name__ == "__main__":
    main()
