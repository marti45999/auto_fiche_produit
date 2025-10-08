"""
Configuration globale du scraper multi-pharmacies.
Regroupe les constantes utilisées par les modules de recherche et d'extraction.
"""

TOR_PROXY = "socks5h://127.0.0.1:9050"
TOR_CONTROL_HOST = "127.0.0.1"
TOR_CONTROL_PORT = 9051
TOR_CONTROL_PASSWORD = ""  # Laisser vide si l'authentification cookie est désactivée
TOR_RENEW_DELAY = 3  # secondes

REQUEST_TIMEOUT = 30  # Timeout par défaut pour les requêtes HTTP
SEARCH_TIMEOUT = 15  # Timeout spécifique aux recherches rapides
MAX_RETRIES = 5  # Nombre de tentatives d'extraction
RETRY_DELAY = 5  # Délai entre les tentatives (en secondes)

DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"
)

TOR_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"
)

IOS_USER_AGENT = (
    "Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) "
    "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 "
    "Mobile/15E148 Safari/604.1"
)

TOR_CHECK_URL = "https://check.torproject.org"
IP_CHECK_URL = "https://ipinfo.io/ip"
