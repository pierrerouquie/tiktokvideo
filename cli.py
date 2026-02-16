#!/usr/bin/env python3
"""
🎬 TikTok Voice Generator — CLI
Génère une vidéo TikTok en une commande. Tout est automatisé.
Optimisé : auto-détection GPU (ROCm/CUDA), multi-threading, VAAPI/NVENC.
"""
import argparse
from pathlib import Path

from core.hardware import get_profile
from core.voice_clone import VoiceCloner
from core.subtitles import SubtitleGenerator
from core.video_maker import VideoMaker
from core.media_fetcher import MediaFetcher


def main():
    parser = argparse.ArgumentParser(
        description="🎬 TikTok Voice Generator — Pipeline 100% automatisé",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemples :
  # Basique (fond auto via Pexels)
  python cli.py -t "Salut ! Voici 3 astuces gaming incroyables." -v ma_voix.wav

  # Avec fond manuel
  python cli.py -t "Hello world!" -v voice.wav --bg fond.jpg --lang en

  # Sans Pexels (fond uni)
  python cli.py -t "Mon texte" -v voice.wav --no-auto-bg --bg-color "#1a1a2e"

  # Export personnalisé
  python cli.py -t "..." -v voice.wav -o video_finale.mp4 --font-size 32
        """,
    )
    # Requis
    parser.add_argument("-t", "--text", required=True, help="Texte à synthétiser")
    parser.add_argument("-v", "--voice", required=True, help="Échantillon voix (.wav, 3-15s)")

    # Optionnels
    parser.add_argument("-o", "--output", default="output/tiktok.mp4", help="Fichier de sortie")
    parser.add_argument("-l", "--lang", default="fr", help="Code langue (fr, en, es...)")
    parser.add_argument("--bg", default=None, help="Image/vidéo de fond manuelle")
    parser.add_argument("--no-auto-bg", action="store_true", help="Désactive la recherche auto Pexels")
    parser.add_argument("--prefer-photo", action="store_true", help="Préférer photos aux vidéos Pexels")
    parser.add_argument("--bg-color", default="#1a1a2e", help="Couleur fond uni (hex)")

    # Paramètres TTS
    parser.add_argument("--tts-mode", choices=["turbo", "quality"], default="turbo",
                        help="Mode TTS : turbo (rapide, 350M) ou quality (multilingue, plus lent)")
    parser.add_argument("--exaggeration", type=float, default=0.6, help="Expressivité (0.0-1.5)")
    parser.add_argument("--cfg-weight", type=float, default=0.5, help="Fidélité texte (0.1-1.0)")

    # Paramètres vidéo
    parser.add_argument("--font-size", type=int, default=28, help="Taille police sous-titres")
    parser.add_argument("--sub-style", choices=["tiktok", "classic"], default="tiktok")
    parser.add_argument("--whisper-model", default="large-v3-turbo",
                        help="Modèle Whisper (large-v3-turbo, large-v3, medium, small)")

    args = parser.parse_args()
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)

    # Afficher le profil matériel détecté
    hw = get_profile()
    print("=" * 60)
    print("🎬 TikTok Voice Generator — Pipeline Automatisé")
    print("=" * 60)
    print(hw.summary())
    print("=" * 60)

    # ── 1. Fond automatique ───────────────────────────────────────────
    bg_path = args.bg or ""
    bg_type = "auto"

    if not args.bg and not args.no_auto_bg:
        print("\n📌 Étape 1/4 — Recherche de fond (Pexels)")
        fetcher = MediaFetcher()
        if fetcher.is_available:
            result = fetcher.auto_fetch_background(
                args.text,
                prefer_video=not args.prefer_photo,
                orientation="portrait",
            )
            bg_path = result["path"]
            bg_type = result["type"]
            print(f"   Mots-clés : {result.get('keywords', [])}")
            print(f"   Type : {bg_type}")
        else:
            print("   ⚠️ PEXELS_API_KEY non configurée → fond uni")
            bg_type = "none"
    elif args.bg:
        print(f"\n📌 Étape 1/4 — Fond manuel : {args.bg}")
    else:
        print(f"\n📌 Étape 1/4 — Fond uni : {args.bg_color}")
        bg_type = "none"

    # ── 2. Voix clonée ────────────────────────────────────────────────
    tts_label = "Chatterbox-Turbo" if args.tts_mode == "turbo" else "Chatterbox Multilingual"
    print(f"\n📌 Étape 2/4 — Clonage vocal ({tts_label})")
    cloner = VoiceCloner(mode=args.tts_mode)
    audio_path = "output/speech.wav"
    cloner.generate(
        text=args.text,
        voice_sample_path=args.voice,
        output_path=audio_path,
        language=args.lang,
        exaggeration=args.exaggeration,
        cfg_weight=args.cfg_weight,
    )

    # ── 3. Sous-titres ────────────────────────────────────────────────
    print(f"\n📌 Étape 3/4 — Sous-titres (Faster-Whisper {args.whisper_model})")
    sub_gen = SubtitleGenerator(model_size=args.whisper_model)
    srt_path = "output/subtitles.srt"
    sub_gen.generate_srt(audio_path, srt_path, language=args.lang, style=args.sub_style)

    # ── 4. Assemblage ─────────────────────────────────────────────────
    print("\n📌 Étape 4/4 — Assemblage vidéo (FFmpeg)")
    maker = VideoMaker()
    maker.create(
        audio_path=audio_path,
        srt_path=srt_path,
        output_path=args.output,
        background_path=bg_path,
        background_type=bg_type,
        bg_color=args.bg_color,
        font_size=args.font_size,
    )

    print("\n" + "=" * 60)
    print(f"🎉 Vidéo prête : {args.output}")
    print("=" * 60)


if __name__ == "__main__":
    main()
