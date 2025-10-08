# 🏥 Scraper Multi-Pharmacies

Scraper Python pour extraire automatiquement les informations produits de 3 pharmacies en ligne françaises via Tor.

## 📋 Sites supportés

- ✅ Cocooncenter - Extraction complète (titre, prix, description, composition, conseils, avis clients)
- ✅ Pharma-GDD - Extraction complète avec anti-blocage 403
- ✅ Pharmacie des Drakkars - Extraction complète avec avis pharmacien

## 🔧 Installation

### 1. Prérequis système

```bash
# Sur Ubuntu/Debian
sudo apt update
sudo apt install tor python3 python3-pip

# Démarrer Tor
sudo systemctl start tor
sudo systemctl enable tor

# Vérifier que Tor fonctionne
curl --socks5 127.0.0.1:9050 https://check.torproject.org | grep -i congratulations
```

### 2. Configuration Tor (pour rotation d'identité)

Éditer le fichier de configuration Tor :

```bash
sudo nano /etc/tor/torrc
```

Ajouter ces lignes :

```
ControlPort 9051
CookieAuthentication 0
```

Redémarrer Tor :

```bash
sudo systemctl restart tor
```

### 3. Installation des dépendances Python

```bash
pip install requests beautifulsoup4 PySocks
```

## 📁 Structure du projet

```
pharma-scraper/
├── main.py          # Point d'entrée principal
├── searchers.py     # Modules de recherche (rapide, sans Tor)
├── scrapers.py      # Scrapers d'extraction (avec Tor)
├── config.py        # Configuration
├── eans.txt         # (optionnel) Liste de codes EAN
└── README.md        # Ce fichier
```

## 🚀 Utilisation

### Mode interactif

```bash
python3 main.py
```

Le programme propose 3 modes :

1. Un seul EAN - Traite un code EAN unique
2. Plusieurs EAN - Traite plusieurs codes séparés par des virgules
3. Fichier - Lit les codes depuis `eans.txt` (un EAN par ligne)

### Exemple de fichier eans.txt

```
3665606001874
3337875762861
1234567890123
```

## 📊 Données extraites

### Cocooncenter

- Titre du produit
- Prix
- Description
- Code EAN
- Contenance
- Forme
- Note et nombre d'avis
- Composition
- Conseils d'utilisation
- Top 5 avis clients (auteur, note, titre, texte)

### Pharma-GDD

- Titre du produit
- Prix
- Description
- Code EAN
- Code custom
- Marque
- Note et nombre d'avis
- Composition
- Conseils d'utilisation
- Top 10 avis clients (auteur, date, note, texte)

### Pharmacie des Drakkars

- Titre du produit
- Prix
- Référence
- Variantes/contenances
- Description complète
- Composition complète
- Note, nombre d'avis et % de recommandation
- Avis client principal (auteur, date, note, texte)
- Conseils du pharmacien

## 💾 Format de sortie

Les résultats sont sauvegardés en JSON :

```json
{
  "cocooncenter": {
    "site": "Cocooncenter",
    "ean": "3665606001874",
    "url": "https://...",
    "titre": "Produit XYZ",
    "prix": "15.99€",
    "note": "4.5/5",
    "nb_avis": "127",
    "description": "...",
    "composition": "...",
    "conseils": "...",
    "avis_clients": [
      {
        "auteur": "Marie P.",
        "note": "5/5",
        "titre": "Excellent produit",
        "avis": "Je recommande vivement..."
      }
    ]
  }
}
```

Fichier de sortie : `product_[EAN].json`

## 🔄 Gestion des erreurs 403 (Pharma-GDD)

Le scraper implémente plusieurs mécanismes anti-blocage :

- Retry automatique - 5 tentatives maximum
- Rotation d'identité Tor - Change le circuit Tor entre chaque tentative
- Délai entre tentatives - 5 secondes d'attente
- Headers réalistes - User-Agent et headers complets

Si le problème persiste :

```bash
# Recharger manuellement Tor
sudo systemctl restart tor

# Vérifier la connexion Tor
curl --socks5 127.0.0.1:9050 https://ipinfo.io/ip
```

## ⚙️ Configuration avancée

Éditer `config.py` pour ajuster :

```python
MAX_RETRIES = 5           # Nombre de tentatives
RETRY_DELAY = 5           # Délai entre tentatives (secondes)
REQUEST_TIMEOUT = 30      # Timeout des requêtes
TOR_CONTROL_PORT = 9051   # Port de contrôle Tor
```

## 🐛 Dépannage

### Tor ne se connecte pas

```bash
# Vérifier le statut
sudo systemctl status tor

# Redémarrer
sudo systemctl restart tor

# Vérifier les logs
sudo journalctl -u tor -f
```

### Erreur "Connection refused"

Le port de contrôle Tor n'est pas activé. Vérifier `/etc/tor/torrc` :

```
ControlPort 9051
CookieAuthentication 0
```

### Produit non trouvé mais existe sur le site

- Vérifier que l'EAN est correct (13 chiffres)
- Certains produits peuvent avoir des EAN multiples (variantes)
- Essayer de rechercher manuellement sur le site

### 403 Forbidden persistant

```bash
# Changer complètement de circuit Tor
sudo systemctl restart tor
sleep 10

# Relancer le scraper
python3 main.py
```

## 📝 Notes importantes

- ⚠️ Respect des CGU - Utilisez ce scraper de manière responsable
- ⏱️ Performance - L'utilisation de Tor ralentit les requêtes (normal)
- 🔒 Anonymat - Toutes les requêtes d'extraction passent par Tor
- 📊 Recherche - La phase de recherche (rapide) n'utilise pas Tor

## 🆘 Support

En cas de problème :

- Vérifier que Tor fonctionne
- Vérifier les dépendances Python
- Consulter les logs d'erreur
- Tester avec un seul EAN d'abord

## 📜 Licence

Usage personnel uniquement. Respectez les conditions d'utilisation des sites web.
