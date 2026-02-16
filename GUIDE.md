# 🎬 Guide — TikTok Voice Generator

## Ton PC (optimisé pour)

| Composant | Spec |
|-----------|------|
| CPU | AMD Ryzen 7 5700X3D — 8 cores / 16 threads, 96MB L3 |
| GPU | AMD Radeon RX 6950 XT — 16GB GDDR6 (ROCm) |
| RAM | 32GB DDR4-3200 |
| Stockage | NVMe PNY CS3030 1TB (rapide) + SSD SATA 1TB + HDD 1TB |
| Carte mère | ASUS TUF GAMING X570-PLUS |

---

## Étape 1 — Installer Ubuntu en dual-boot

1. Télécharge Ubuntu 22.04 LTS (ou 24.04) depuis https://ubuntu.com/download/desktop
2. Crée une clé USB bootable avec Rufus (Windows) ou Balena Etcher
3. Redémarre ton PC, accède au BIOS (touche DEL au démarrage sur ta carte ASUS)
4. Boot sur la clé USB → "Installer Ubuntu à côté de Windows"
5. Alloue **au moins 100GB** sur ton NVMe (CS3030) pour Ubuntu — c'est le disque le plus rapide
6. Termine l'installation, redémarre → tu choisis Windows ou Ubuntu au démarrage

---

## Étape 2 — Installation automatique (1 commande)

Ouvre un terminal sur Ubuntu et lance :

```bash
# Cloner le repo
git clone https://github.com/pierrerouquie/tiktokvideo.git
cd tiktokvideo

# Lancer l'installation automatique
chmod +x setup.sh
./setup.sh
```

**C'est tout.** Le script :
- Met à jour Ubuntu
- Installe FFmpeg, Python 3.11
- Détecte ton GPU AMD RX 6950 XT → installe ROCm + VAAPI
- Installe PyTorch ROCm (GPU accéléré)
- Installe toutes les dépendances Python
- Vérifie que tout fonctionne

> Si tu vois `✅ GPU détecté et fonctionnel !` à la fin → tout est bon.

---

## Étape 3 — Préparer ta voix

Tu as besoin d'un échantillon de ta voix :
- **Durée** : 5 à 15 secondes
- **Format** : WAV (ou MP3, le système convertit)
- **Qualité** : Parle clairement, pas de bruit de fond, pas de musique
- **Contenu** : Dis n'importe quoi, lis un texte, parle normalement

Enregistre avec ton tel ou un micro, mets le fichier dans `assets/voices/`.

---

## Étape 4 — (Optionnel) Fond automatique Pexels

Pour que l'outil trouve automatiquement des vidéos/images de fond :

1. Va sur https://www.pexels.com/api/ → crée un compte gratuit
2. Clique "Your API Key" → copie la clé
3. Ajoute-la dans ton terminal :

```bash
# Ajouter dans ~/.bashrc pour que ce soit permanent
echo 'export PEXELS_API_KEY="ta_clé_ici"' >> ~/.bashrc
source ~/.bashrc
```

> Sans Pexels, l'outil utilise un fond uni coloré. Ça marche quand même.

---

## Étape 5 — Utilisation

### Option A : Interface Web (le plus simple)

```bash
cd tiktokvideo
source .venv/bin/activate
python app.py
```

→ Ouvre http://localhost:7860 dans ton navigateur

1. **Tape ton texte** dans la zone de texte
2. **Upload ta voix** (ou enregistre avec le micro)
3. **Choisis la langue** (Français par défaut)
4. Clique **🚀 Générer la vidéo**
5. La vidéo apparaît à droite → télécharge-la

### Option B : Ligne de commande (rapide)

```bash
cd tiktokvideo
source .venv/bin/activate

# Commande basique
python cli.py -t "Salut ! Voici 3 astuces gaming incroyables." -v assets/voices/ma_voix.wav

# Avec options
python cli.py \
  -t "Mon texte pour TikTok" \
  -v assets/voices/ma_voix.wav \
  -o output/ma_video.mp4 \
  --lang fr \
  --exaggeration 0.7 \
  --font-size 32
```

---

## Options avancées

| Option | Défaut | Description |
|--------|--------|-------------|
| `--lang` | `fr` | Langue : fr, en, es, de, it, pt, ja, zh, ko, ar... |
| `--exaggeration` | `0.6` | Expressivité voix (0.0=monotone → 1.5=très expressif) |
| `--cfg-weight` | `0.5` | Fidélité au texte (0.3=naturel → 0.7=très fidèle) |
| `--font-size` | `28` | Taille des sous-titres |
| `--sub-style` | `tiktok` | `tiktok` (2 mots) ou `classic` (phrase entière) |
| `--bg` | auto | Image/vidéo de fond manuelle |
| `--bg-color` | `#1a1a2e` | Couleur si fond uni |
| `--no-auto-bg` | off | Désactive Pexels (fond uni) |
| `--whisper-model` | `large-v3` | Modèle Whisper (`small` = rapide, `large-v3` = précis) |

---

## Ce qui se passe sous le capot

```
Ton texte
  ↓
[1] Pexels API → cherche un fond vidéo/image en rapport avec le texte
  ↓
[2] Chatterbox TTS (GPU ROCm) → clone ta voix et dit le texte
  ↓
[3] Faster-Whisper (CPU 16 threads) → crée les sous-titres synchronisés
  ↓
[4] FFmpeg (VAAPI hardware) → assemble tout en 1080x1920 (9:16 TikTok)
  ↓
ta_video.mp4 → prête pour TikTok !
```

### Optimisations pour ta config :

- **Chatterbox TTS** : tourne sur le GPU (RX 6950 XT, 16GB VRAM) via ROCm → float16 half precision
- **Faster-Whisper** : utilise les 16 threads du Ryzen 7 5700X3D avec int8 quantization (CTranslate2 ne supporte pas ROCm)
- **FFmpeg** : encodage vidéo hardware VAAPI (GPU) + 12 threads CPU en fallback
- **Téléchargements** : 4 fichiers en parallèle, chunks de 32KB optimisés NVMe

---

## Dépannage

**"ROCm non détecté"** → Redémarre après `setup.sh`, vérifie que ton user est dans les groupes `render` et `video` :
```bash
sudo usermod -aG render,video $USER
# Puis déconnecte/reconnecte ta session
```

**"FFmpeg erreur VAAPI"** → L'outil fallback automatiquement sur l'encodage software. Pas de panique, ça marche.

**"CUDA not available"** → Normal sur AMD. Le code utilise ROCm qui se présente comme "cuda" via PyTorch. Vérifie avec :
```bash
python -c "import torch; print(torch.cuda.is_available(), torch.version.hip)"
```

**Première exécution lente** → Normal, les modèles se téléchargent (~3GB). Les lancements suivants sont rapides.

**"Out of memory"** → Ferme les autres applications GPU (jeux, navigateur avec accélération hardware). Le modèle TTS prend ~6-8GB VRAM.
