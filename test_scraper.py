#!/usr/bin/env python3
"""
Script de test pour vérifier que le scraper et l'environnement fonctionnent correctement.
"""

import sys

import requests

from config import IP_CHECK_URL, TOR_CHECK_URL
from scrapers import TorSession
from searchers import CocooncenterSearcher, DrakkarsSearcher, PharmaGDDSearcher


def test_tor_connection() -> bool:
    """Teste la connexion Tor en effectuant deux requêtes."""
    print("🔍 Test de connexion Tor...")
    try:
        session = TorSession.create_session()
        response = session.get(TOR_CHECK_URL, timeout=10)

        if "Congratulations" in response.text:
            print("   ✅ Tor fonctionne correctement")
            ip_response = session.get(IP_CHECK_URL, timeout=10)
            print(f"   🌐 IP Tor: {ip_response.text.strip()}")
            return True

        print("   ❌ Tor ne fonctionne pas correctement")
        return False
    except Exception as exc:  # noqa: BLE001
        print(f"   ❌ Erreur: {exc}")
        return False


def test_searchers() -> dict:
    """Teste les modules de recherche rapide."""
    print("\n🔍 Test des modules de recherche...")

    test_ean = "3665606001874"  # Pierre fabre capsule respiratoire
    results = {}

    print("\n   📦 Test Cocooncenter...")
    try:
        searcher = CocooncenterSearcher()
        found, url = searcher.search(test_ean)
        results["cocooncenter"] = found
        if found:
            print("      ✅ Produit trouvé")
            print(f"      🔗 {url[:80]}...")
        else:
            print("      ❌ Produit non trouvé")
    except Exception as exc:  # noqa: BLE001
        print(f"      ❌ Erreur: {exc}")
        results["cocooncenter"] = False

    print("\n   📦 Test Pharma-GDD...")
    try:
        searcher = PharmaGDDSearcher()
        found, url, label = searcher.search(test_ean)
        results["pharmagdd"] = found
        if found:
            print(f"      ✅ Produit trouvé: {label}")
            print(f"      🔗 {url[:80]}...")
        else:
            print("      ❌ Produit non trouvé")
    except Exception as exc:  # noqa: BLE001
        print(f"      ❌ Erreur: {exc}")
        results["pharmagdd"] = False

    print("\n   📦 Test Pharmacie des Drakkars...")
    try:
        searcher = DrakkarsSearcher()
        found, url = searcher.search(test_ean)
        results["drakkars"] = found
        if found:
            print("      ✅ Produit trouvé")
            print(f"      🔗 {url[:80]}...")
        else:
            print("      ❌ Produit non trouvé")
    except Exception as exc:  # noqa: BLE001
        print(f"      ❌ Erreur: {exc}")
        results["drakkars"] = False

    return results


def test_dependencies() -> bool:
    """Vérifie que les bibliothèques Python nécessaires sont installées."""
    print("\n🔍 Test des dépendances Python...")

    dependencies = {
        "requests": None,
        "bs4": "beautifulsoup4",
        "socks": "PySocks",
    }

    all_ok = True
    for module, package in dependencies.items():
        try:
            __import__(module)
            print(f"   ✅ {package or module} installé")
        except ImportError:
            print(f"   ❌ {package or module} manquant")
            print(f"      Installation: pip3 install {package or module}")
            all_ok = False

    return all_ok


def main() -> None:
    """Point d'entrée du script de test."""
    print("╔═══════════════════════════════════════════════════════════╗")
    print("║        TEST DU SCRAPER MULTI-PHARMACIES                  ║")
    print("╚═══════════════════════════════════════════════════════════╝\n")

    print("═══════════════════════════════════════════════════════════")
    print("TEST 1 : Dépendances Python")
    print("═══════════════════════════════════════════════════════════")
    deps_ok = test_dependencies()

    if not deps_ok:
        print("\n❌ Des dépendances sont manquantes. Installez-les avant de continuer.")
        sys.exit(1)

    print("\n═══════════════════════════════════════════════════════════")
    print("TEST 2 : Connexion Tor")
    print("═══════════════════════════════════════════════════════════")
    tor_ok = test_tor_connection()

    if not tor_ok:
        print("\n⚠️  Tor ne fonctionne pas. Vérifiez :")
        print("   1. Tor est installé : sudo apt install tor")
        print("   2. Tor est démarré : sudo systemctl start tor")
        print("   3. Configuration : /etc/tor/torrc")
        print("\nLes tests de scraping ne seront pas effectués.")

    print("\n═══════════════════════════════════════════════════════════")
    print("TEST 3 : Modules de recherche")
    print("═══════════════════════════════════════════════════════════")
    search_results = test_searchers()

    print("\n═══════════════════════════════════════════════════════════")
    print("RÉSUMÉ DES TESTS")
    print("═══════════════════════════════════════════════════════════")

    print(f"\n{'Composant':<30} {'Status':<20}")
    print("─" * 50)
    print(f"{'Dépendances Python':<30} {'✅ OK' if deps_ok else '❌ Erreur':<20}")
    print(f"{'Connexion Tor':<30} {'✅ OK' if tor_ok else '❌ Erreur':<20}")
    print(f"{'Recherche Cocooncenter':<30} {'✅ OK' if search_results.get('cocooncenter') else '❌ Erreur':<20}")
    print(f"{'Recherche Pharma-GDD':<30} {'✅ OK' if search_results.get('pharmagdd') else '❌ Erreur':<20}")
    print(f"{'Recherche Drakkars':<30} {'✅ OK' if search_results.get('drakkars') else '❌ Erreur':<20}")

    print("\n═══════════════════════════════════════════════════════════")

    all_tests_ok = deps_ok and tor_ok and all(search_results.values())

    if all_tests_ok:
        print("\n✅ TOUS LES TESTS SONT PASSÉS")
        print("\n🚀 Vous pouvez lancer le scraper avec : python3 main.py")
    else:
        print("\n⚠️  CERTAINS TESTS ONT ÉCHOUÉ")
        print("\nVérifiez les erreurs ci-dessus avant de lancer le scraper.")

        if not tor_ok:
            print("\n💡 Conseil : Commencez par réparer Tor")
            print("   sudo systemctl restart tor")

        if not all(search_results.values()):
            print("\n💡 Les recherches peuvent échouer si :")
            print("   - Le produit de test n'existe plus sur le site")
            print("   - Le site est temporairement indisponible")
            print("   - Votre connexion internet a un problème")

    print("\n═══════════════════════════════════════════════════════════\n")


if __name__ == "__main__":
    main()
