# 🎬 TikTok Voice Generator

Pipeline **100% automatisé** pour créer des vidéos courtes (TikTok / Reels / Shorts) avec ta voix clonée.

**Tu tapes ton texte. Tu cliques. C'est tout.**

## Ce que ça fait

1. **Analyse ton texte** et extrait les mots-clés
2. **Cherche automatiquement** un fond vidéo/image sur Pexels (gratuit)
3. **Clone ta voix** à partir d'un échantillon de 5-15 secondes
4. **Génère les sous-titres** synchronisés mot par mot (style TikTok)
5. **Assemble le tout** en vidéo 9:16 prête à poster

## Stack (100% open source & gratuit)

| Composant | Outil | Licence |
|-----------|-------|---------|
| Voice Cloning | Chatterbox Multilingual | MIT |
| Sous-titres | Faster-Whisper (large-v3) | MIT |
| Fond auto | Pexels API | Gratuit |
| Assemblage | FFmpeg | LGPL |
| Interface | Gradio | Apache 2.0 |

## Installation

```bash
git clone <repo> && cd tiktok-voice-generator
python3.11 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # Ajouter ta clé Pexels (optionnel)
```

## Utilisation

```bash
# Interface web
python app.py          # → http://localhost:7860

# Ligne de commande
python cli.py -t "Mon texte ici" -v assets/voices/ma_voix.wav
```

## Prérequis

- Python 3.11
- GPU NVIDIA 6 Go+ VRAM (CUDA 12+)
- FFmpeg (`sudo apt install ffmpeg`)
- Clé API Pexels (optionnel, gratuit sur [pexels.com/api](https://www.pexels.com/api/))
