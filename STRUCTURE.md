# Architecture du projet

## Vue d'ensemble

```
pharma-scraper/
│
├── main.py              # Point d'entrée et orchestration
├── searchers.py         # Modules de recherche (sans Tor)
├── scrapers.py          # Scrapers d'extraction (avec Tor)
├── config.py            # Configuration globale
│
├── install.sh           # Script d'installation
├── test_scraper.py      # Script de test
├── eans.txt             # Fichier d'entrée (optionnel)
│
├── README.md            # Documentation utilisateur
├── CHANGELOG.md         # Historique des versions
├── TODO.md              # Améliorations futures
├── requirements.txt     # Dépendances Python
└── .gitignore           # Fichiers à ignorer
```

## Flux de traitement

```
┌─────────────────┐
│  Entrée EAN(s)  │
└────────┬────────┘
         │
         ▼
┌─────────────────────────┐
│  Phase 1: RECHERCHE     │
│  (searchers.py)         │
│  - Sans Tor (rapide)    │
│  - Vérifie disponibilité│
└────────┬────────────────┘
         │
         ▼
┌─────────────────────────┐
│  Phase 2: EXTRACTION    │
│  (scrapers.py)          │
│  - Via Tor (anonyme)    │
│  - Données complètes    │
└────────┬────────────────┘
         │
         ▼
┌─────────────────────────┐
│  Phase 3: EXPORT        │
│  - Affichage console    │
│  - Sauvegarde JSON      │
└─────────────────────────┘
```

## Classes principales

### main.py
- `MasterScraper`: Orchestrateur principal
- `SearchResult`: Structure de résultat de recherche

### searchers.py
- `BaseSearcher`: Classe de base
- `CocooncenterSearcher`: Recherche Cocooncenter
- `PharmaGDDSearcher`: Recherche Pharma-GDD
- `DrakkarsSearcher`: Recherche Drakkars

### scrapers.py
- `TorSession`: Gestion des sessions Tor
- `BaseScraper`: Classe de base avec retry
- `CocooncenterScraper`: Extraction Cocooncenter
- `PharmaGDDScraper`: Extraction Pharma-GDD
- `DrakkarsScraper`: Extraction Drakkars

## Principe de fonctionnement

1. **Séparation recherche/extraction**
   - Recherche rapide sans Tor pour vérifier disponibilité
   - Extraction via Tor uniquement si produit trouvé

2. **Gestion des erreurs**
   - Retry automatique avec backoff
   - Rotation d'identité Tor en cas de blocage
   - Logs détaillés pour debugging

3. **Modularité**
   - Chaque site a son propre scraper
   - Facile d'ajouter de nouveaux sites
   - Configuration centralisée

## Ajout d'un nouveau site

1. Créer une classe dans `searchers.py`:
```python
class NouveauSiteSearcher(BaseSearcher):
    def search(self, ean: str):
        # Logique de recherche
        return found, url
```

2. Créer une classe dans `scrapers.py`:
```python
class NouveauSiteScraper(BaseScraper):
    def extract(self, url: str, ean: str):
        # Logique d'extraction
        return product_dict
```

3. Ajouter dans `main.py`:
```python
self.searchers['nouveausite'] = NouveauSiteSearcher()
self.scrapers['nouveausite'] = NouveauSiteScraper()
```
