# 🎬 TikTok Voice Generator — Guide Complet

## Vue d'ensemble

Pipeline entièrement automatisé pour générer des vidéos courtes (TikTok, Reels, Shorts) à partir d'un simple texte et d'un échantillon de voix.

**Pipeline :** `Texte → Pexels (fond auto) → Chatterbox (voix clonée) → Faster-Whisper (sous-titres) → FFmpeg (vidéo 9:16)`

Tout est **open source**, **gratuit**, et fonctionne **en local** sur ta machine.

---

## Stack Technologique 2026

| Composant | Outil | Version | Licence | Rôle |
|-----------|-------|---------|---------|------|
| Voice Cloning + TTS | **Chatterbox Multilingual** (Resemble AI) | 0.1.6+ | MIT | Clone ta voix, génère l'audio en 23 langues |
| Sous-titres | **Faster-Whisper** | large-v3 | MIT | Transcription avec timestamps mot par mot |
| Fond automatique | **Pexels API** | v1 | Gratuit | Vidéos/images de stock selon les mots-clés du texte |
| Assemblage vidéo | **FFmpeg** | 6+ | LGPL | Combine fond + audio + sous-titres en MP4 |
| Interface web | **Gradio** | 5+ | Apache 2.0 | UI dans le navigateur |

### Pourquoi ces choix ?

- **Chatterbox Multilingual** : sorti fin 2025 par Resemble AI, c'est le meilleur TTS open source en 2026. Il surpasse XTTS v2 et supporte le français nativement. Voice cloning zero-shot à partir de ~5 secondes d'audio.
- **Faster-Whisper** : implémentation CTranslate2 de Whisper large-v3. 4x plus rapide que le Whisper original d'OpenAI, avec timestamps mot par mot essentiels pour le style TikTok.
- **Pexels API** : gratuite, sans attribution requise, 150 000+ vidéos. Élimine le besoin de chercher des fonds manuellement.

---

## Prérequis Machine

| Composant | Minimum | Recommandé |
|-----------|---------|------------|
| OS | Ubuntu 22.04 / Win 10 / macOS | Ubuntu 24.04 |
| GPU | NVIDIA 6 Go VRAM (GTX 1660) | NVIDIA 8 Go+ (RTX 3070+) |
| RAM | 16 Go | 32 Go |
| Python | 3.11 | 3.11 |
| Stockage | 10 Go libre (modèles) | 20 Go |
| FFmpeg | 5+ | 6+ |

---

## Étape 1 — Cloner et installer

```bash
# Cloner le projet
git clone <url-du-repo> tiktok-voice-generator
cd tiktok-voice-generator

# Créer l'environnement Python 3.11
python3.11 -m venv .venv
source .venv/bin/activate   # Linux/Mac
# .venv\Scripts\activate    # Windows

# Installer les dépendances
pip install --upgrade pip
pip install -r requirements.txt
```

### Installer FFmpeg

```bash
# Ubuntu/Debian
sudo apt update && sudo apt install ffmpeg

# macOS
brew install ffmpeg

# Windows
choco install ffmpeg
```

### Vérifier CUDA

```bash
python -c "import torch; print(f'CUDA: {torch.cuda.is_available()}, GPU: {torch.cuda.get_device_name(0) if torch.cuda.is_available() else \"CPU\"}')"
```

---

## Étape 2 — Configurer Pexels (optionnel mais recommandé)

1. Va sur [pexels.com/api](https://www.pexels.com/api/)
2. Crée un compte gratuit
3. Génère une clé API
4. Configure-la :

```bash
cp .env.example .env
# Édite .env et remplace ton_api_key_ici par ta vraie clé
```

Ou en variable d'environnement :
```bash
export PEXELS_API_KEY="ta_clé_ici"
```

Sans Pexels, le pipeline utilise un fond uni coloré (configurable).

---

## Étape 3 — Préparer ton échantillon vocal

Pour un clonage de qualité :

1. **Durée** : 5 à 15 secondes (sweet spot pour Chatterbox)
2. **Environnement** : pièce calme, pas de bruit de fond
3. **Micro** : un micro USB, casque gaming, ou même le micro du téléphone
4. **Contenu** : parle naturellement avec des phrases variées
5. **Format** : WAV 16 bits (Audacity gratuit pour enregistrer/découper)

```bash
# Place ton fichier dans :
cp ma_voix.wav assets/voices/ma_voix.wav
```

---

## Étape 4 — Utilisation

### Interface Web (recommandé)

```bash
python app.py
# Ouvre http://localhost:7860
```

L'interface propose :
- Zone de texte pour le script
- Upload ou enregistrement micro pour ta voix
- Choix de la langue (23 disponibles)
- Fond automatique via Pexels (ou upload manuel)
- Paramètres avancés (expressivité, style sous-titres, couleurs...)
- Bouton "Générer" → vidéo prête en quelques minutes

### Ligne de commande

```bash
# Basique — tout automatisé
python cli.py \
  -t "Salut tout le monde ! Aujourd'hui je vous montre 3 astuces de gaming incroyables." \
  -v assets/voices/ma_voix.wav

# Avec fond manuel
python cli.py -t "Mon texte" -v ma_voix.wav --bg fond.jpg

# En anglais, plus expressif
python cli.py -t "Hey guys, check this out!" -v voice.wav -l en --exaggeration 0.8

# Fond uni personnalisé (sans Pexels)
python cli.py -t "Mon texte" -v ma_voix.wav --no-auto-bg --bg-color "#0f0f23"

# Toutes les options
python cli.py --help
```

---

## Étape 5 — Structure du projet

```
tiktok-voice-generator/
├── CLAUDE.md                 # Instructions pour Claude Code
├── README.md                 # Documentation rapide
├── PROJECT.md                # Ce fichier (guide complet)
├── .env.example              # Template de configuration
├── .gitignore
├── requirements.txt
│
├── app.py                    # Interface web Gradio
├── cli.py                    # Interface ligne de commande
│
├── core/
│   ├── __init__.py
│   ├── voice_clone.py        # VoiceCloner (Chatterbox Multilingual)
│   ├── subtitles.py          # SubtitleGenerator (Faster-Whisper)
│   ├── video_maker.py        # VideoMaker (FFmpeg)
│   └── media_fetcher.py      # MediaFetcher (Pexels API + extraction mots-clés)
│
├── assets/
│   ├── voices/               # Échantillons voix de référence
│   ├── backgrounds/          # Fonds téléchargés (cache Pexels)
│   └── fonts/                # Polices custom (optionnel)
│
├── output/                   # Vidéos, audios, SRT générés
│
└── .claude/
    └── commands/
        └── generate.md       # Commande Claude Code custom
```

---

## Étape 6 — Utiliser avec Claude Code

Le projet est conçu pour fonctionner avec Claude Code. Le fichier `CLAUDE.md` à la racine donne à Claude tout le contexte nécessaire.

### Commandes utiles dans Claude Code

```
# Demander à Claude de générer une vidéo
"Génère une vidéo TikTok avec le texte suivant : [ton texte]. Utilise ma_voix.wav."

# Demander à Claude d'ajouter une fonctionnalité
"Ajoute un module qui permet de choisir une musique de fond en plus de la voix."

# Demander à Claude de debug
"L'erreur FFmpeg dit 'No such filter: subtitles'. Comment fixer ?"
```

### Workflow recommandé

1. Ouvre Claude Code dans le dossier du projet
2. Claude lit automatiquement `CLAUDE.md`
3. Demande des modifications ou améliorations
4. Claude fait les changements, teste, et commit

---

## Étape 7 — Améliorations possibles

| Amélioration | Comment | Difficulté |
|-------------|---------|------------|
| Musique de fond | Pydub : mixer un MP3 avec l'audio voix | Facile |
| Effets zoom/pan variables | FFmpeg : randomiser les paramètres zoompan | Facile |
| Batch : 10 vidéos d'un coup | Boucle Python sur une liste de textes | Facile |
| Avatar parlant | SadTalker ou Wav2Lip (lip sync sur photo) | Moyen |
| Génération d'images IA | FLUX.2 klein (Apache 2.0, 4B params, ~6 Go VRAM) | Moyen |
| Génération vidéo IA | Wan 2.1 T2V 1.3B (~8 Go VRAM) | Avancé |
| Traduction automatique | Argos Translate (open source, local) | Facile |
| API REST | FastAPI wrapper autour du pipeline | Moyen |

---

## Dépannage

### "CUDA out of memory"
→ Réduis le modèle Whisper : `--whisper-model medium` ou `small`

### "No such filter: subtitles" (FFmpeg)
→ FFmpeg doit être compilé avec libass :
```bash
sudo apt install libass-dev
# ou réinstaller ffmpeg : sudo apt install --reinstall ffmpeg
```

### "PEXELS_API_KEY non configurée"
→ Crée un compte gratuit sur [pexels.com/api](https://www.pexels.com/api/) et configure la variable d'environnement.

### Qualité de voix médiocre
→ Vérifie ton échantillon : 5-15s, pas de bruit, voix claire.
→ Ajuste `exaggeration` (0.5-0.8) et `cfg_weight` (0.3-0.5).

### Sous-titres désynchronisés
→ Assure-toi que l'audio est propre (pas de longs silences au début/fin).

---

## Commandes rapides

```bash
# Installation complète
pip install -r requirements.txt

# Lancer l'interface web
python app.py

# Générer via CLI
python cli.py -t "Mon texte" -v ma_voix.wav

# Tester le voice cloning seul
python -c "from core.voice_clone import VoiceCloner; c = VoiceCloner(); c.generate('Test', 'assets/voices/sample.wav', 'test.wav')"

# Tester Pexels seul
python -c "from core.media_fetcher import MediaFetcher; m = MediaFetcher(); print(m.extract_keywords('Les meilleures astuces gaming pour devenir pro'))"
```
