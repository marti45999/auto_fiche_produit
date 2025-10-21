#!/usr/bin/env python3
"""
Serveur Flask pour l'interface web du scraper.
Gère la réception des codes EAN depuis la page web et lance le scraping.
"""

from __future__ import annotations

import json
import os
import threading
from typing import Dict, List

from dotenv import load_dotenv
from flask import Flask, jsonify, render_template, request, send_from_directory
from flask_cors import CORS

from main import MasterScraper
from api_checker import PharmazonAPIChecker
from webhook_notifier import WebhookNotifier

# Charger les variables d'environnement depuis le fichier .env
load_dotenv()

app = Flask(__name__, static_folder="web", static_url_path="", template_folder="web")
CORS(app)

# URL du webhook pour les notifications (configurable via variable d'environnement)
WEBHOOK_URL = os.getenv("WEBHOOK_URL")
WEBHOOK_URL_PDTS = os.getenv("WEBHOOK_URL_PDTS")

# Initialiser les utilitaires
api_checker = PharmazonAPIChecker()
webhook_notifier = WebhookNotifier(WEBHOOK_URL, WEBHOOK_URL_PDTS)


def process_scraping_task(data: dict):
    """
    Fonction exécutée en arrière-plan pour traiter le scraping.
    Cette fonction s'exécute dans un thread séparé.
    """
    try:
        print(f"\n{'=' * 70}")
        print(f"🚀 DÉMARRAGE DU TRAITEMENT EN ARRIÈRE-PLAN")
        print(f"{'=' * 70}\n")

        if not data or "eans" not in data:
            print(f"❌ ERREUR: Format de données invalide - {data}")
            return

        eans_list = data["eans"]
        ignored_3400 = data.get("ignored3400", [])

        if not isinstance(eans_list, list):
            print(f"❌ ERREUR: Liste de codes EAN invalide - Type: {type(eans_list)}")
            return

        scraper = MasterScraper()
        results = []
        not_found_backend = []
        processed_count = 0
        skipped_count = 0
        error_count = 0

        print(f"\n{'=' * 70}")
        print(f"📋 Produits ignorés (EAN commençant par 3400): {len(ignored_3400)}")
        print(f"📋 Produits à traiter: {len(eans_list)}")
        print(f"{'=' * 70}")

        # Afficher tous les EAN reçus
        print(f"\n🔍 LISTE DES EAN REÇUS:")
        for idx, ean_entry in enumerate(eans_list, 1):
            primary = ean_entry.get("primary") if isinstance(ean_entry, dict) else ean_entry
            replacement = ean_entry.get("replacement") if isinstance(ean_entry, dict) else None
            print(f"   #{idx}: Primary={primary}, Replacement={replacement}")
        print(f"{'=' * 70}\n")

        for idx, ean_entry in enumerate(eans_list, 1):
            try:
                print(f"\n{'🔄' * 35}")
                print(f"🔄 TRAITEMENT DU PRODUIT #{idx}/{len(eans_list)}")
                print(f"{'🔄' * 35}")

                primary_ean = (ean_entry.get("primary") or "").strip()
                replacement_ean = (ean_entry.get("replacement") or "").strip()

                print(f"📝 EAN Primary: {primary_ean}")
                print(f"📝 EAN Replacement: {replacement_ean if replacement_ean else 'Aucun'}")

                if not primary_ean:
                    print(f"⚠️  SKIP: EAN vide - passage au produit suivant")
                    skipped_count += 1
                    continue

                # Vérifier d'abord si le produit existe dans le backend
                print(f"\n{'=' * 70}")
                print(f"🔎 ÉTAPE 1: Vérification backend pour l'EAN: {primary_ean}")
                print(f"{'=' * 70}")

                exists, backend_data = api_checker.check_product_exists(primary_ean)

                if not exists:
                    print(f"❌ Produit non trouvé côté backend - ignoré")
                    not_found_backend.append(primary_ean)

                    result_entry = {
                        "primary_ean": primary_ean,
                        "replacement_ean": replacement_ean if replacement_ean else None,
                        "found": False,
                        "backend_exists": False,
                        "products": {},
                    }
                    results.append(result_entry)
                    processed_count += 1
                    continue

                print(f"✅ Produit trouvé côté backend: {backend_data.get('name', 'N/A')}")

                # Tenter avec le code EAN principal
                print(f"\n{'=' * 70}")
                print(f"🔎 ÉTAPE 2: Scraping pour l'EAN: {primary_ean}")
                print(f"{'=' * 70}")

                search_results = scraper.search_all_sites(primary_ean)
                print(f"🔍 Résultats de recherche obtenus pour {len(search_results)} site(s)")

                print(f"\n{'=' * 70}")
                print(f"📦 ÉTAPE 3: Extraction des données")
                print(f"{'=' * 70}")
                products = scraper.extract_products(primary_ean, search_results)
                print(f"✅ Extraction terminée - {len(products)} produit(s) extrait(s)")

                # Si aucun produit trouvé et qu'il y a un code de remplacement
                if not products and replacement_ean:
                    print(f"\n⚠️  Aucun produit trouvé pour {primary_ean}")
                    print(f"🔄 Tentative avec le code EAN de remplacement: {replacement_ean}\n")

                    search_results = scraper.search_all_sites(replacement_ean)
                    products = scraper.extract_products(replacement_ean, search_results)

                    if products:
                        # Indiquer qu'on a utilisé le code de remplacement
                        print(f"✅ Produits trouvés avec le code de remplacement!")
                        for site_key in products:
                            products[site_key]["used_replacement"] = True
                            products[site_key]["original_ean"] = primary_ean
                    else:
                        print(f"❌ Aucun produit trouvé même avec le code de remplacement")

                # Ajouter le résultat
                result_entry = {
                    "primary_ean": primary_ean,
                    "replacement_ean": replacement_ean if replacement_ean else None,
                    "found": len(products) > 0,
                    "backend_exists": True,
                    "backend_data": backend_data,
                    "products": products,
                }

                results.append(result_entry)
                processed_count += 1

                # ÉTAPE 4: Sauvegarde et envoi webhook
                print(f"\n{'=' * 70}")
                print(f"💾 ÉTAPE 4: Sauvegarde et envoi webhook")
                print(f"{'=' * 70}")

                # Déterminer l'EAN utilisé pour la recherche (pour le nom de fichier)
                ean_used_for_search = replacement_ean if (replacement_ean and any(p.get("used_replacement", False) for p in products.values())) else primary_ean

                if products:
                    # Produit trouvé : sauvegarder dans un fichier JSON
                    json_file = f"product_{ean_used_for_search}.json"
                    with open(json_file, "w", encoding="utf-8") as f:
                        json.dump(products, f, ensure_ascii=False, indent=2)
                    print(f"💾 Résultats sauvegardés dans: {json_file}")
                else:
                    # Produit non trouvé mais existe côté backend : pas de sauvegarde JSON
                    print(f"⚠️  Aucune donnée à sauvegarder (produit non trouvé sur les sites)")

                # Envoyer TOUJOURS le webhook (même si products est vide)
                # IMPORTANT: On envoie TOUJOURS le primary_ean (code EAN actuel) dans le webhook,
                # même si le produit a été trouvé avec le code remplacé (ancien code EAN)
                print(f"📤 Envoi du webhook pour l'EAN actuel {primary_ean} (trouvé via: {ean_used_for_search}, données: {'présentes' if products else 'vides'})")
                webhook_notifier.send_product_data(primary_ean, products if products else {})

                print(f"\n✅ PRODUIT #{idx} TERMINÉ AVEC SUCCÈS")

            except Exception as e:
                error_count += 1
                print(f"\n{'❌' * 35}")
                print(f"❌ ERREUR LORS DU TRAITEMENT DU PRODUIT #{idx}")
                print(f"{'❌' * 35}")
                print(f"EAN: {primary_ean if 'primary_ean' in locals() else 'N/A'}")
                print(f"Type d'erreur: {type(e).__name__}")
                print(f"Message: {str(e)}")
                print(f"{'❌' * 35}\n")

                # Ajouter un résultat d'erreur
                result_entry = {
                    "primary_ean": primary_ean if 'primary_ean' in locals() else None,
                    "replacement_ean": replacement_ean if 'replacement_ean' in locals() else None,
                    "found": False,
                    "backend_exists": False,
                    "error": str(e),
                    "products": {},
                }
                results.append(result_entry)

                # Continuer avec le produit suivant
                continue

        # Résumé final du traitement
        print(f"\n{'🎯' * 35}")
        print(f"🎯 RÉSUMÉ FINAL DU TRAITEMENT")
        print(f"{'🎯' * 35}")
        print(f"📊 Produits reçus: {len(eans_list)}")
        print(f"✅ Produits traités avec succès: {processed_count}")
        print(f"⚠️  Produits ignorés (EAN vide): {skipped_count}")
        print(f"❌ Produits en erreur: {error_count}")
        print(f"📦 Résultats au total: {len(results)}")
        print(f"{'🎯' * 35}\n")

        # Détail des résultats
        success_count = sum(1 for r in results if r.get("found"))
        not_found_scraping = sum(1 for r in results if r.get("backend_exists") and not r.get("found"))

        print(f"📈 DÉTAIL DES RÉSULTATS:")
        print(f"   ✅ Produits trouvés et scrapés: {success_count}")
        print(f"   ❌ Produits non trouvés (backend): {len(not_found_backend)}")
        print(f"   ❌ Produits non trouvés (scraping): {not_found_scraping}")
        print(f"   🚫 Produits ignorés (EAN 3400): {len(ignored_3400)}")

        # Envoyer la notification par webhook si nécessaire
        print(f"\n{'=' * 70}")
        print(f"🔍 VÉRIFICATION DES NOTIFICATIONS:")
        print(f"   - Produits ignorés (3400): {len(ignored_3400)}")
        print(f"   - Produits non trouvés (backend): {len(not_found_backend)}")
        print(f"{'=' * 70}\n")

        if ignored_3400 or not_found_backend:
            print(f"\n{'=' * 70}")
            print("📧 Envoi de la notification récapitulative...")
            print(f"{'=' * 70}\n")
            webhook_notifier.send_summary_email(ignored_3400, not_found_backend)
        else:
            print("ℹ️  Aucune notification d'erreur à envoyer")

        print(f"\n{'✅' * 35}")
        print(f"✅ TRAITEMENT COMPLET TERMINÉ")
        print(f"{'✅' * 35}\n")

    except Exception as exc:
        print(f"\n{'💥' * 35}")
        print(f"💥 ERREUR CRITIQUE LORS DU SCRAPING")
        print(f"{'💥' * 35}")
        print(f"Type d'erreur: {type(exc).__name__}")
        print(f"Message: {str(exc)}")
        print(f"{'💥' * 35}\n")

        import traceback
        print("📋 Traceback complet:")
        traceback.print_exc()


@app.route("/")
def index():
    """Page d'accueil - Interface web."""
    return render_template("index.html")


@app.route("/api/scrape", methods=["POST"])
def scrape_products():
    """
    Endpoint API pour lancer le scraping en mode asynchrone.

    Accepte un JSON avec la structure:
    {
        "eans": [
            {"primary": "3401548610299", "replacement": "3401548610298"},
            {"primary": "1234567890123", "replacement": null}
        ],
        "ignored3400": ["3400123456789", ...]
    }

    Retourne immédiatement un 202 (Accepted) et traite la requête en arrière-plan.
    """
    try:
        data = request.get_json()

        print(f"\n{'=' * 70}")
        print(f"📥 RÉCEPTION DE LA REQUÊTE DE SCRAPING")
        print(f"{'=' * 70}")
        print(f"📦 Payload reçu: {json.dumps(data, indent=2, ensure_ascii=False)}")
        print(f"{'=' * 70}\n")

        if not data or "eans" not in data:
            print(f"❌ ERREUR: Format de données invalide - {data}")
            return jsonify({"error": "Format de données invalide"}), 400

        eans_list = data.get("eans", [])
        ignored_3400 = data.get("ignored3400", [])

        if not isinstance(eans_list, list):
            print(f"❌ ERREUR: Liste de codes EAN invalide - Type: {type(eans_list)}")
            return jsonify({"error": "Liste de codes EAN invalide"}), 400

        # Afficher les informations de la requête
        print(f"📋 Produits ignorés (EAN commençant par 3400): {len(ignored_3400)}")
        print(f"📋 Produits à traiter: {len(eans_list)}")

        # Lancer le traitement en arrière-plan dans un thread
        thread = threading.Thread(
            target=process_scraping_task,
            args=(data,),
            daemon=True
        )
        thread.start()

        print(f"\n{'✅' * 35}")
        print(f"✅ TRAITEMENT LANCÉ EN ARRIÈRE-PLAN")
        print(f"{'✅' * 35}")
        print(f"Thread ID: {thread.ident}")
        print(f"Les webhooks seront envoyés au fur et à mesure du traitement.\n")

        # Retourner immédiatement une réponse 202 (Accepted)
        return jsonify({
            "success": True,
            "message": "Scraping lancé en arrière-plan",
            "status": "processing",
            "total_products": len(eans_list),
            "thread_id": thread.ident
        }), 202

    except Exception as exc:
        print(f"\n{'💥' * 35}")
        print(f"💥 ERREUR LORS DU LANCEMENT DU SCRAPING")
        print(f"{'💥' * 35}")
        print(f"Type d'erreur: {type(exc).__name__}")
        print(f"Message: {str(exc)}")
        print(f"{'💥' * 35}\n")

        import traceback
        print("📋 Traceback complet:")
        traceback.print_exc()

        return jsonify({"error": str(exc), "type": type(exc).__name__}), 500


@app.route("/api/health", methods=["GET"])
def health_check():
    """Vérification que le serveur est en ligne."""
    return jsonify({"status": "ok"})


if __name__ == "__main__":
    print(f"╔{'═' * 68}╗")
    print(f"║{'  SERVEUR WEB - Interface de scraping':^68}║")
    print(f"╚{'═' * 68}╝\n")
    print("📡 Serveur démarré sur http://127.0.0.1:8080")
    print("🌐 Ouvrez votre navigateur à cette adresse\n")
    print("⚠️  Mode debug désactivé pour éviter les doublons de webhooks\n")

    # debug=False pour éviter les redémarrages automatiques qui créent des doublons de webhooks
    app.run(debug=False, host="0.0.0.0", port=8080)
