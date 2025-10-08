# 📚 Exemples d'utilisation

Ce guide présente différents cas d'usage du scraper multi-pharmacies.

---

## 🎯 Cas d'usage basiques

### 1. Scraper un seul produit

```bash
python3 main.py
# Choisir option 1
# Entrer l'EAN : 3337875762861
```

**Résultat :**
- Recherche sur les 3 sites
- Extraction complète des données
- Fichier `product_3337875762861.json` créé

---

### 2. Scraper plusieurs produits

```bash
python3 main.py
# Choisir option 2
# Entrer : 3337875762861, 3282770114139, 3665606001874
```

**Résultat :**
- 3 fichiers JSON créés
- Rapport dans la console pour chaque produit

---

### 3. Scraper depuis un fichier

**Créer `eans.txt` :**

```
3337875762861
3282770114139
3665606001874
```

**Lancer :**

```bash
python3 main.py
# Choisir option 3
```

**Résultat :**
- Traitement séquentiel de tous les EAN
- Un fichier JSON par produit

---

## 🔧 Utilisation avancée

### 4. Utilisation programmatique

**Créer `my_script.py` :**

```python
#!/usr/bin/env python3
from main import MasterScraper

# Créer le scraper
scraper = MasterScraper()

# Liste d'EAN à traiter
eans = [
    "3337875762861",
    "3282770114139",
    "3665606001874"
]

# Traiter tous les EAN
for ean in eans:
    print(f"\n{'='*50}")
    print(f"Traitement de {ean}")
    print(f"{'='*50}")
    
    # Recherche
    results = scraper.search_all_sites(ean)
    
    # Extraction
    products = scraper.extract_products(ean, results)
    
    # Affichage
    scraper.display_results(products, ean)
```

---

### 5. Scraper uniquement un site spécifique

**Créer `scraper_single_site.py` :**

```python
#!/usr/bin/env python3
from searchers import CocooncenterSearcher
from scrapers import CocooncenterScraper

ean = "3337875762861"

# Recherche
searcher = CocooncenterSearcher()
found, url = searcher.search(ean)

if found:
    print(f"✅ Produit trouvé : {url}")
    
    # Extraction
    scraper = CocooncenterScraper()
    product = scraper.extract(url, ean)
    
    print(f"\nTitre : {product['titre']}")
    print(f"Prix : {product['prix']}")
    print(f"Note : {product.get('note', 'N/A')}")
else:
    print("❌ Produit non trouvé")
```

---

### 6. Export personnalisé (CSV)

**Créer `export_csv.py` :**

```python
#!/usr/bin/env python3
import csv
from main import MasterScraper

def export_to_csv(ean):
    """Exporte les résultats en CSV"""
    scraper = MasterScraper()
    
    # Recherche et extraction
    results = scraper.search_all_sites(ean)
    products = scraper.extract_products(ean, results)
    
    # Export CSV
    with open(f'product_{ean}.csv', 'w', encoding='utf-8', newline='') as f:
        writer = csv.writer(f)
        
        # En-tête
        writer.writerow(['Site', 'Titre', 'Prix', 'Note', 'Nb Avis', 'URL'])
        
        # Données
        for site, product in products.items():
            writer.writerow([
                product.get('site', ''),
                product.get('titre', ''),
                product.get('prix', ''),
                product.get('note', ''),
                product.get('nb_avis', ''),
                product.get('url', '')
            ])
    
    print(f"✅ Export CSV : product_{ean}.csv")

# Utilisation
export_to_csv("3337875762861")
```

---

### 7. Comparateur de prix

**Créer `price_comparator.py` :**

```python
#!/usr/bin/env python3
from main import MasterScraper
import re

def compare_prices(ean):
    """Compare les prix d'un produit sur tous les sites"""
    scraper = MasterScraper()
    
    results = scraper.search_all_sites(ean)
    products = scraper.extract_products(ean, results)
    
    if not products:
        print("❌ Produit non trouvé")
        return
    
    print(f"\n{'='*60}")
    print(f"COMPARATEUR DE PRIX - EAN: {ean}")
    print(f"{'='*60}\n")
    
    # Extraire les prix
    prices = {}
    for site, product in products.items():
        prix_str = product.get('prix', '')
        match = re.search(r'([0-9,]+)', prix_str)
        if match:
            prix_float = float(match.group(1).replace(',', '.'))
            prices[site] = {
                'prix': prix_float,
                'titre': product.get('titre', ''),
                'url': product.get('url', '')
            }
    
    sorted_prices = sorted(prices.items(), key=lambda x: x[1]['prix'])
    
    for i, (site, info) in enumerate(sorted_prices, 1):
        medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else "  "
        print(f"{medal} {site.upper():<20} {info['prix']:.2f}€")
    
    if sorted_prices:
        best = sorted_prices[0]
        print(f"\n💰 MEILLEUR PRIX : {best[1]['prix']:.2f}€ sur {best[0].upper()}")
        print(f"🔗 {best[1]['url']}")

compare_prices("3337875762861")
```

---

### 8. Surveillance des avis

**Créer `monitor_reviews.py` :**

```python
#!/usr/bin/env python3
from main import MasterScraper

def monitor_reviews(ean):
    """Surveille les nouveaux avis clients"""
    scraper = MasterScraper()
    
    results = scraper.search_all_sites(ean)
    products = scraper.extract_products(ean, results)
    
    print(f"\n{'='*60}")
    print(f"SURVEILLANCE DES AVIS - EAN: {ean}")
    print(f"{'='*60}\n")
    
    for site, product in products.items():
        print(f"\n🏪 {product['site']}")
        print(f"{'─'*60}")
        
        avis_clients = product.get('avis_clients', [])
        
        if not avis_clients:
            print("   Aucun avis disponible")
            continue
        
        print(f"   📊 Total avis : {product.get('nb_avis', 'N/A')}")
        print(f"   ⭐ Note moyenne : {product.get('note', 'N/A')}")
        print(f"\n   📝 Derniers avis :")
        
        for i, avis in enumerate(avis_clients[:3], 1):
            print(f"\n   Avis #{i}")
            print(f"   👤 {avis.get('auteur', 'Anonyme')}")
            if 'date' in avis:
                print(f"   📅 {avis['date']}")
            print(f"   ⭐ {avis.get('note', 'N/A')}")
            texte = avis.get('avis', '')
            short = texte[:100] + "..." if len(texte) > 100 else texte
            print(f"   💬 {short}")

monitor_reviews("3337875762861")
```

---

### 9. Batch processing avec logging

**Créer `batch_scraper.py` :**

```python
#!/usr/bin/env python3
import logging
from datetime import datetime
from main import MasterScraper

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f'scraping_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'),
        logging.StreamHandler()
    ]
)

def batch_scrape(eans_file):
    """Scrape un lot d'EAN avec logging"""
    scraper = MasterScraper()
    
    with open(eans_file, 'r', encoding='utf-8') as f:
        eans = [line.strip() for line in f if line.strip() and not line.startswith('#')]
    
    logging.info("Début du batch - %d produits à traiter", len(eans))
    
    stats = {
        'total': len(eans),
        'success': 0,
        'errors': 0,
        'not_found': 0
    }
    
    for idx, ean in enumerate(eans, 1):
        logging.info("[%d/%d] Traitement EAN: %s", idx, len(eans), ean)
        try:
            results = scraper.search_all_sites(ean)
            found_count = sum(1 for r in results.values() if r.found)
            
            if found_count == 0:
                logging.warning("EAN %s non trouvé sur aucun site", ean)
                stats['not_found'] += 1
                continue
            
            products = scraper.extract_products(ean, results)
            
            if products:
                logging.info("✅ EAN %s traité - %d site(s)", ean, len(products))
                stats['success'] += 1
            else:
                logging.error("❌ Échec extraction EAN %s", ean)
                stats['errors'] += 1
        except Exception as exc:  # noqa: BLE001
            logging.exception("❌ Erreur EAN %s: %s", ean, exc)
            stats['errors'] += 1
    
    logging.info("="*60)
    logging.info("RAPPORT FINAL")
    logging.info("="*60)
    logging.info("Total : %d", stats['total'])
    logging.info("Succès : %d", stats['success'])
    logging.info("Erreurs : %d", stats['errors'])
    logging.info("Non trouvés : %d", stats['not_found'])
    if stats['total']:
        logging.info("Taux de succès : %.1f%%", stats['success']/stats['total']*100)

batch_scrape('eans.txt')
```

---

## 🛠️ Debugging et dépannage

### 10. Mode debug détaillé

**Créer `debug_scraper.py` :**

```python
#!/usr/bin/env python3
import logging
from scrapers import CocooncenterScraper

logging.basicConfig(level=logging.DEBUG)

ean = "3337875762861"
url = "https://www.cocooncenter.com/..."

scraper = CocooncenterScraper()

try:
    product = scraper.extract(url, ean)
    print("\n✅ Extraction réussie")
    print(f"Titre: {product.get('titre')}")
    print(f"Prix: {product.get('prix')}")
except Exception as exc:  # noqa: BLE001
    print(f"\n❌ Erreur: {exc}")
    import traceback
    traceback.print_exc()
```

---

## 📊 Analyse des données

### 11. Statistiques globales

**Créer `stats.py` :**

```python
#!/usr/bin/env python3
import glob
import json
import re
from collections import defaultdict

def analyze_results():
    """Analyse tous les fichiers JSON de résultats"""
    files = glob.glob('product_*.json')
    
    if not files:
        print("❌ Aucun fichier de résultats trouvé")
        return
    
    stats = {
        'total_products': len(files),
        'by_site': defaultdict(int),
        'avg_price': [],
        'avg_rating': []
    }
    
    for file in files:
        with open(file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        for site, product in data.items():
            stats['by_site'][site] += 1
            
            prix_str = product.get('prix', '')
            if prix_str:
                match = re.search(r'([0-9,]+)', prix_str)
                if match:
                    stats['avg_price'].append(float(match.group(1).replace(',', '.')))
            
            note_str = product.get('note', '')
            if note_str:
                match = re.search(r'([0-9.]+)', note_str)
                if match:
                    stats['avg_rating'].append(float(match.group(1)))
    
    print(f"\n{'='*60}")
    print("STATISTIQUES GLOBALES")
    print(f"{'='*60}\n")
    print(f"📦 Produits analysés : {stats['total_products']}")
    print("\n🏪 Par site :")
    for site, count in stats['by_site'].items():
        print(f"   - {site}: {count} produits")
    
    if stats['avg_price']:
        avg_price = sum(stats['avg_price']) / len(stats['avg_price'])
        print(f"\n💰 Prix moyen : {avg_price:.2f}€")
    
    if stats['avg_rating']:
        avg_rating = sum(stats['avg_rating']) / len(stats['avg_rating'])
        print(f"⭐ Note moyenne : {avg_rating:.2f}/5")

analyze_results()
```

---

Ces exemples couvrent les cas d'usage les plus courants. N'hésitez pas à les adapter selon vos besoins !
