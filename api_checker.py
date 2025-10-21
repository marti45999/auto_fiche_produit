#!/usr/bin/env python3
"""
Utilitaire pour vérifier l'existence des produits via l'API backend Pharmazon.
"""

from __future__ import annotations

import os
import requests
from typing import Optional
from urllib.parse import urlencode


class PharmazonAPIChecker:
    """Vérifie l'existence des produits dans le backend Pharmazon via l'API."""

    def __init__(self):
        """Initialise le checker avec les headers requis."""
        self.BASE_URL = os.getenv("PHARMAZON_BASE_URL")
        self.BEARER_TOKEN = os.getenv("PHARMAZON_BEARER_TOKEN")
        self.USER_AGENT = os.getenv("PHARMAZON_USER_AGENT")

        self.headers = {
            "Authorization": f"Bearer {self.BEARER_TOKEN}",
            "Content-Type": "application/json",
            "User-Agent": self.USER_AGENT,
        }

    def check_product_exists(self, ean: str) -> tuple[bool, Optional[dict]]:
        """
        Vérifie si un produit existe dans le backend via son code EAN.

        Args:
            ean: Le code EAN du produit à vérifier

        Returns:
            Un tuple (existe, données) où:
            - existe: True si le produit existe, False sinon
            - données: Les données du produit si trouvé, None sinon
        """
        # Construire les paramètres de recherche
        search_criteria = {
            "searchCriteria[filter_groups][0][filters][0][field]": "ean",
            "searchCriteria[filter_groups][0][filters][0][value]": ean,
            "searchCriteria[filter_groups][0][filters][0][condition_type]": "eq",
        }

        url = f"{self.BASE_URL}?{urlencode(search_criteria)}"

        try:
            response = requests.get(url, headers=self.headers, timeout=10)
            response.raise_for_status()

            data = response.json()

            # Vérifier si des produits ont été trouvés
            if data.get("total_count", 0) > 0 and data.get("items"):
                return True, data["items"][0]
            else:
                return False, None

        except requests.exceptions.RequestException as e:
            print(f"⚠️  Erreur lors de la vérification de l'EAN {ean}: {e}")
            return False, None

    def batch_check_products(self, eans: list[str]) -> dict[str, tuple[bool, Optional[dict]]]:
        """
        Vérifie l'existence de plusieurs produits.

        Args:
            eans: Liste des codes EAN à vérifier

        Returns:
            Un dictionnaire avec les EAN comme clés et (existe, données) comme valeurs
        """
        results = {}

        for ean in eans:
            print(f"🔍 Vérification de l'EAN: {ean}")
            exists, data = self.check_product_exists(ean)

            if exists:
                print(f"  ✅ Produit trouvé: {data.get('name', 'N/A')}")
            else:
                print(f"  ❌ Produit non trouvé")

            results[ean] = (exists, data)

        return results
