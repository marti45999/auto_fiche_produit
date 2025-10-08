#!/bin/bash

echo "╔═══════════════════════════════════════════════════════════╗"
echo "║     INSTALLATION - SCRAPER MULTI-PHARMACIES               ║"
echo "╚═══════════════════════════════════════════════════════════╝"
echo ""

# Couleurs
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Fonction pour afficher les messages
print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_info() {
    echo -e "ℹ️  $1"
}

# Vérifier si on est root pour certaines opérations
if [ "$EUID" -ne 0 ]; then 
    print_warning "Ce script nécessite des droits sudo pour installer Tor"
    USE_SUDO="sudo"
else
    USE_SUDO=""
fi

echo "═══════════════════════════════════════════════════════════"
echo "ÉTAPE 1 : Vérification du système"
echo "═══════════════════════════════════════════════════════════"
echo ""

# Détecter l'OS
if [ -f /etc/os-release ]; then
    . /etc/os-release
    OS=$ID
    print_info "Système détecté : $PRETTY_NAME"
else
    print_error "Impossible de détecter le système d'exploitation"
    exit 1
fi

echo ""
echo "═══════════════════════════════════════════════════════════"
echo "ÉTAPE 2 : Installation de Tor"
echo "═══════════════════════════════════════════════════════════"
echo ""

# Vérifier si Tor est déjà installé
if command -v tor &> /dev/null; then
    print_success "Tor est déjà installé"
    tor --version | head -1
else
    print_info "Installation de Tor..."
    
    case $OS in
        ubuntu|debian)
            $USE_SUDO apt update
            $USE_SUDO apt install -y tor
            ;;
        centos|rhel|fedora)
            $USE_SUDO yum install -y tor || $USE_SUDO dnf install -y tor
            ;;
        arch|manjaro)
            $USE_SUDO pacman -S --noconfirm tor
            ;;
        *)
            print_error "Distribution non supportée. Installez Tor manuellement."
            exit 1
            ;;
    esac
    
    if [ $? -eq 0 ]; then
        print_success "Tor installé avec succès"
    else
        print_error "Échec de l'installation de Tor"
        exit 1
    fi
fi

echo ""
echo "═══════════════════════════════════════════════════════════"
echo "ÉTAPE 3 : Configuration de Tor"
echo "═══════════════════════════════════════════════════════════"
echo ""

# Backup du fichier torrc
if [ -f /etc/tor/torrc ]; then
    $USE_SUDO cp /etc/tor/torrc /etc/tor/torrc.backup.$(date +%Y%m%d_%H%M%S)
    print_success "Backup de torrc créé"
fi

# Vérifier si la configuration existe déjà
if grep -q "^ControlPort 9051" /etc/tor/torrc 2>/dev/null; then
    print_success "Configuration Tor déjà présente"
else
    print_info "Ajout de la configuration Tor..."
    
    $USE_SUDO tee -a /etc/tor/torrc > /dev/null <<EOF

# Configuration pour le scraper multi-pharmacies
ControlPort 9051
CookieAuthentication 0
EOF
    
    print_success "Configuration ajoutée à /etc/tor/torrc"
fi

echo ""
echo "═══════════════════════════════════════════════════════════"
echo "ÉTAPE 4 : Démarrage de Tor"
echo "═══════════════════════════════════════════════════════════"
echo ""

# Redémarrer Tor
$USE_SUDO systemctl restart tor

# Attendre que Tor démarre
sleep 3

# Vérifier le statut
if $USE_SUDO systemctl is-active --quiet tor; then
    print_success "Tor est actif et fonctionne"
    
    # Activer au démarrage
    $USE_SUDO systemctl enable tor
    print_success "Tor activé au démarrage"
else
    print_error "Tor ne démarre pas correctement"
    print_info "Vérifiez les logs avec : sudo journalctl -u tor -n 50"
    exit 1
fi

# Tester la connexion Tor
print_info "Test de connexion Tor..."
if curl -s --socks5 127.0.0.1:9050 https://check.torproject.org | grep -q "Congratulations"; then
    print_success "Connexion Tor fonctionnelle !"
else
    print_warning "Impossible de vérifier la connexion Tor"
fi

echo ""
echo "═══════════════════════════════════════════════════════════"
echo "ÉTAPE 5 : Installation de Python et dépendances"
echo "═══════════════════════════════════════════════════════════"
echo ""

# Vérifier Python
if command -v python3 &> /dev/null; then
    print_success "Python3 est installé"
    python3 --version
else
    print_info "Installation de Python3..."
    
    case $OS in
        ubuntu|debian)
            $USE_SUDO apt install -y python3 python3-pip
            ;;
        centos|rhel|fedora)
            $USE_SUDO yum install -y python3 python3-pip || $USE_SUDO dnf install -y python3 python3-pip
            ;;
        arch|manjaro)
            $USE_SUDO pacman -S --noconfirm python python-pip
            ;;
    esac
fi

# Installer les dépendances Python
print_info "Installation des dépendances Python..."

pip3 install --user requests beautifulsoup4 PySocks

if [ $? -eq 0 ]; then
    print_success "Dépendances Python installées"
else
    print_error "Échec de l'installation des dépendances Python"
    exit 1
fi

echo ""
echo "═══════════════════════════════════════════════════════════"
echo "ÉTAPE 6 : Vérification finale"
echo "═══════════════════════════════════════════════════════════"
echo ""

# Vérifier que tous les fichiers sont présents
files=("main.py" "searchers.py" "scrapers.py" "config.py")
all_present=true

for file in "${files[@]}"; do
    if [ -f "$file" ]; then
        print_success "$file présent"
    else
        print_error "$file manquant"
        all_present=false
    fi
done

echo ""

if [ "$all_present" = true ]; then
    echo "╔═══════════════════════════════════════════════════════════╗"
    echo "║          ✅ INSTALLATION TERMINÉE AVEC SUCCÈS             ║"
    echo "╚═══════════════════════════════════════════════════════════╝"
    echo ""
    print_success "Tous les composants sont installés et configurés"
    echo ""
    print_info "Pour lancer le scraper :"
    echo "   python3 main.py"
    echo ""
    print_info "Pour tester Tor :"
    echo "   curl --socks5 127.0.0.1:9050 https://ipinfo.io/ip"
    echo ""
else
    print_error "Installation incomplète - des fichiers sont manquants"
    exit 1
fi

echo "═══════════════════════════════════════════════════════════"
echo "INFORMATIONS UTILES"
echo "═══════════════════════════════════════════════════════════"
echo ""
echo "📝 Fichiers de configuration :"
echo "   - Tor : /etc/tor/torrc"
echo "   - Scraper : ./config.py"
echo ""
echo "🔧 Commandes utiles :"
echo "   - Redémarrer Tor : sudo systemctl restart tor"
echo "   - Statut Tor : sudo systemctl status tor"
echo "   - Logs Tor : sudo journalctl -u tor -f"
echo ""
echo "📖 Documentation : README.md"
echo ""
