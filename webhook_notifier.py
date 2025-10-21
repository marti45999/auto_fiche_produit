#!/usr/bin/env python3
"""
Utilitaire pour envoyer des notifications par webhook (email).
"""

from __future__ import annotations

import requests
from typing import List


class WebhookNotifier:
    """Envoie des notifications par webhook."""

    def __init__(self, webhook_url: str, webhook_url_pdts: str = None):
        """
        Initialise le notifier avec l'URL du webhook.

        Args:
            webhook_url: L'URL du webhook pour l'envoi des notifications récapitulatives
            webhook_url_pdts: L'URL du webhook pour l'envoi des produits scrappés
        """
        self.webhook_url = webhook_url
        self.webhook_url_pdts = webhook_url_pdts

    def send_summary_email(
        self,
        ignored_3400: List[str],
        not_found_backend: List[str],
    ) -> bool:
        """
        Envoie un email récapitulatif via webhook.

        Args:
            ignored_3400: Liste des codes EAN commençant par 3400 (ignorés)
            not_found_backend: Liste des codes EAN non trouvés côté backend

        Returns:
            True si l'envoi a réussi, False sinon
        """
        # Construire le message
        message_parts = []

        if ignored_3400:
            message_parts.append("📋 **Produits ignorés (codes EAN commençant par 3400):**\n")
            for ean in ignored_3400:
                message_parts.append(f"  • {ean}")
            message_parts.append("")

        if not_found_backend:
            message_parts.append("❌ **Produits non trouvés côté backend:**\n")
            for ean in not_found_backend:
                message_parts.append(f"  • {ean}")
            message_parts.append("")

        if not message_parts:
            print("ℹ️  Aucune notification à envoyer (pas de produits ignorés ou non trouvés)")
            return True

        message_parts.insert(0, "🔔 **Rapport de traitement des codes EAN**\n")
        message = "\n".join(message_parts)

        # Payload pour le webhook
        payload = {
            "message": message,
            "ignored_3400_count": len(ignored_3400),
            "not_found_backend_count": len(not_found_backend),
            "ignored_3400": ignored_3400,
            "not_found_backend": not_found_backend,
        }

        try:
            print(f"📧 Envoi de la notification par webhook...")
            response = requests.post(
                self.webhook_url,
                json=payload,
                timeout=10,
            )
            response.raise_for_status()

            print(f"✅ Notification envoyée avec succès!")
            return True

        except requests.exceptions.RequestException as e:
            print(f"⚠️  Erreur lors de l'envoi de la notification: {e}")
            return False

    def send_product_data(self, ean: str, product_data: dict) -> bool:
        """
        Envoie les données d'un produit scrappé via webhook.

        Args:
            ean: Le code EAN du produit
            product_data: Les données complètes du produit (contenu du JSON)

        Returns:
            True si l'envoi a réussi, False sinon
        """
        if not self.webhook_url_pdts:
            print("⚠️  Aucune URL de webhook pour les produits configurée (WEBHOOK_URL_PDTS)")
            return False

        # Payload avec les données du produit
        payload = {
            "ean": ean,
            "data": product_data,
        }

        try:
            print(f"📤 Envoi du produit {ean} au webhook...")
            response = requests.post(
                self.webhook_url_pdts,
                json=payload,
                timeout=10,
            )
            response.raise_for_status()

            print(f"✅ Produit {ean} envoyé avec succès au webhook!")
            return True

        except requests.exceptions.RequestException as e:
            print(f"⚠️  Erreur lors de l'envoi du produit {ean}: {e}")
            return False
