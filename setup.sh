#!/bin/bash
# ══════════════════════════════════════════════════════════════
# 🎬 TikTok Voice Generator — Installation Ubuntu One-Click
# ══════════════════════════════════════════════════════════════
# Compatible : Ubuntu 22.04 / 24.04
# GPU : AMD ROCm (RX 6000/7000), NVIDIA CUDA, ou CPU
# Usage : chmod +x setup.sh && ./setup.sh
# ══════════════════════════════════════════════════════════════

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

print_step() { echo -e "\n${BLUE}══════════════════════════════════════════${NC}"; echo -e "${GREEN}$1${NC}"; echo -e "${BLUE}══════════════════════════════════════════${NC}"; }
print_warn() { echo -e "${YELLOW}⚠️  $1${NC}"; }
print_ok()   { echo -e "${GREEN}✅ $1${NC}"; }
print_err()  { echo -e "${RED}❌ $1${NC}"; }

# ── Vérifications ─────────────────────────────────────────────
if [[ "$OSTYPE" != "linux-gnu"* ]]; then
    print_err "Ce script est pour Ubuntu Linux uniquement."
    exit 1
fi

# ── 1. Mise à jour système ────────────────────────────────────
print_step "1/6 — Mise à jour système"
sudo apt update && sudo apt upgrade -y

# ── 2. Dépendances système ────────────────────────────────────
print_step "2/6 — Installation des dépendances système"
sudo apt install -y \
    python3.11 python3.11-venv python3.11-dev python3-pip \
    ffmpeg \
    git curl wget \
    libsndfile1 libportaudio2

# Vérifier FFmpeg
if command -v ffmpeg &>/dev/null; then
    print_ok "FFmpeg installé : $(ffmpeg -version | head -1)"
else
    print_err "FFmpeg non installé !"
    exit 1
fi

# ── 3. Détection GPU ─────────────────────────────────────────
print_step "3/6 — Détection GPU"

GPU_TYPE="cpu"

# Détecter AMD
if lspci | grep -i "VGA\|3D" | grep -qi "AMD\|Radeon"; then
    echo "GPU AMD détecté !"

    # Installer ROCm si pas déjà installé
    if ! command -v rocminfo &>/dev/null; then
        print_warn "ROCm non installé. Installation..."

        # Ajouter le repo AMD ROCm
        wget -qO - https://repo.radeon.com/rocm/rocm.gpg.key | sudo apt-key add -
        echo "deb [arch=amd64] https://repo.radeon.com/rocm/apt/6.2 jammy main" | sudo tee /etc/apt/sources.list.d/rocm.list
        sudo apt update

        sudo apt install -y rocm-dev rocm-libs
        sudo usermod -aG render,video "$USER"
        print_warn "Redémarre ta session après l'installation pour que ROCm fonctionne."
    fi

    if command -v rocminfo &>/dev/null; then
        print_ok "ROCm installé"
        GPU_TYPE="rocm"
    fi

    # VAAPI pour FFmpeg (encodage hardware)
    sudo apt install -y mesa-va-drivers vainfo
    if vainfo &>/dev/null 2>&1; then
        print_ok "VAAPI (encodage vidéo hardware) disponible"
    else
        print_warn "VAAPI non disponible — FFmpeg utilisera l'encodage software"
    fi

# Détecter NVIDIA
elif lspci | grep -i "VGA\|3D" | grep -qi "NVIDIA"; then
    echo "GPU NVIDIA détecté !"

    if command -v nvidia-smi &>/dev/null; then
        print_ok "Drivers NVIDIA installés"
        GPU_TYPE="cuda"
    else
        print_warn "Drivers NVIDIA non installés."
        print_warn "Installe-les via : sudo apt install nvidia-driver-535"
    fi
else
    print_warn "Pas de GPU dédié détecté — mode CPU uniquement"
fi

echo ""
echo "Type GPU sélectionné : $GPU_TYPE"

# ── 4. Environnement Python ──────────────────────────────────
print_step "4/6 — Création de l'environnement Python"

cd "$(dirname "$0")"
VENV_DIR=".venv"

if [ ! -d "$VENV_DIR" ]; then
    python3.11 -m venv "$VENV_DIR"
    print_ok "Environnement virtuel créé : $VENV_DIR"
else
    print_ok "Environnement virtuel existant : $VENV_DIR"
fi

source "$VENV_DIR/bin/activate"
pip install --upgrade pip wheel setuptools

# ── 5. Installation PyTorch (selon GPU) ──────────────────────
print_step "5/6 — Installation PyTorch + dépendances"

if [ "$GPU_TYPE" = "rocm" ]; then
    echo "Installation PyTorch ROCm (AMD GPU)..."
    pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/rocm6.2
elif [ "$GPU_TYPE" = "cuda" ]; then
    echo "Installation PyTorch CUDA (NVIDIA GPU)..."
    pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu124
else
    echo "Installation PyTorch CPU..."
    pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu
fi

# Installer les dépendances du projet
pip install -r requirements.txt

# ── 6. Vérification ──────────────────────────────────────────
print_step "6/6 — Vérification de l'installation"

python3 -c "
from core.hardware import detect_hardware
hw = detect_hardware()
print()
print(hw.summary())
print()
if hw.gpu_available:
    print('✅ GPU détecté et fonctionnel !')
else:
    print('⚠️  Mode CPU uniquement (fonctionne, mais plus lent pour le TTS)')
print()
print('✅ Installation terminée avec succès !')
"

# ── Résumé ────────────────────────────────────────────────────
echo ""
echo -e "${GREEN}══════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}   🎬 Installation terminée !${NC}"
echo -e "${GREEN}══════════════════════════════════════════════════════════${NC}"
echo ""
echo "Pour lancer l'interface web :"
echo "  source .venv/bin/activate"
echo "  python app.py"
echo ""
echo "Pour utiliser en ligne de commande :"
echo "  source .venv/bin/activate"
echo "  python cli.py -t \"Ton texte\" -v ta_voix.wav"
echo ""
echo "(Optionnel) Pour les fonds automatiques :"
echo "  export PEXELS_API_KEY=\"ta_clé_api_pexels\""
echo "  → Clé gratuite sur https://www.pexels.com/api/"
echo ""
