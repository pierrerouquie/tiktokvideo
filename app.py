"""
🎬 TikTok Voice Generator — Interface Web (Gradio)
Pipeline 100% automatisé : Texte → Fond auto → Voix clonée → Sous-titres → Vidéo
Optimisé : auto-détection GPU (ROCm/CUDA), multi-threading CPU, VAAPI/NVENC.
"""
import gradio as gr
from pathlib import Path

from core.hardware import get_profile
from core.voice_clone import VoiceCloner
from core.subtitles import SubtitleGenerator
from core.video_maker import VideoMaker
from core.media_fetcher import MediaFetcher

# Détection matérielle au démarrage
hw = get_profile()
print("=" * 60)
print("🎬 TikTok Voice Generator — Démarrage")
print("=" * 60)
print(hw.summary())
print("=" * 60)

# Dossiers
for d in ["output", "assets/voices", "assets/backgrounds"]:
    Path(d).mkdir(parents=True, exist_ok=True)

# Modules (lazy loading pour les modèles lourds)
cloner = VoiceCloner()
video_maker = VideoMaker()
media_fetcher = MediaFetcher()
_subtitle_gen = None


def get_subtitle_gen() -> SubtitleGenerator:
    global _subtitle_gen
    if _subtitle_gen is None:
        _subtitle_gen = SubtitleGenerator(model_size="large-v3")
    return _subtitle_gen


def generate_video(
    text: str,
    voice_sample,
    language: str,
    auto_background: bool,
    manual_background,
    prefer_video_bg: bool,
    subtitle_style: str,
    font_size: int,
    exaggeration: float,
    cfg_weight: float,
    bg_color: str,
    progress=gr.Progress(),
):
    """Pipeline complet automatisé."""
    if not text.strip():
        return None, "❌ Entre du texte."
    if voice_sample is None:
        return None, "❌ Fournis un échantillon de ta voix (3-15s)."

    try:
        # ── 1. Fond automatique ───────────────────────────────────────
        progress(0.05, desc="🔍 Recherche de fond...")
        bg_path = ""
        bg_type = "none"

        if auto_background and media_fetcher.is_available:
            result = media_fetcher.auto_fetch_background(
                text, prefer_video=prefer_video_bg, orientation="portrait",
            )
            bg_path = result["path"]
            bg_type = result["type"]
            keywords_info = ", ".join(result.get("keywords", []))
        elif manual_background:
            bg_path = manual_background
            bg_type = "auto"
            keywords_info = "manuel"
        else:
            keywords_info = "fond uni"

        # ── 2. Voix clonée ────────────────────────────────────────────
        progress(0.2, desc="🎙️ Clonage vocal...")
        audio_path = "output/speech.wav"
        cloner.generate(
            text=text,
            voice_sample_path=voice_sample,
            output_path=audio_path,
            language=language,
            exaggeration=exaggeration,
            cfg_weight=cfg_weight,
        )

        # ── 3. Sous-titres ────────────────────────────────────────────
        progress(0.55, desc="📝 Sous-titres...")
        srt_path = "output/subtitles.srt"
        style = "tiktok" if subtitle_style == "TikTok (2 mots)" else "classic"
        get_subtitle_gen().generate_srt(audio_path, srt_path, language=language, style=style)

        # ── 4. Assemblage vidéo ───────────────────────────────────────
        progress(0.8, desc="🎬 Assemblage...")
        video_path = "output/tiktok_video.mp4"
        video_maker.create(
            audio_path=audio_path,
            srt_path=srt_path,
            output_path=video_path,
            background_path=bg_path,
            background_type=bg_type,
            bg_color=bg_color,
            font_size=font_size,
            sub_position="center",
        )

        progress(1.0, desc="✅ Terminé !")
        status = f"✅ Vidéo générée ! Fond : {bg_type} ({keywords_info})"
        return video_path, status

    except Exception as e:
        return None, f"❌ Erreur : {e}"


# ══════════════════════════════════════════════════════════════════════
# INTERFACE GRADIO
# ══════════════════════════════════════════════════════════════════════

with gr.Blocks(title="🎬 TikTok Voice Generator", theme=gr.themes.Soft()) as app:

    # Info matérielle pour l'affichage
    _gpu_info = f"{hw.gpu_name} ({hw.gpu_backend})" if hw.gpu_available else "CPU uniquement"
    _enc_info = hw.ffmpeg_hw_accel.upper() if hw.ffmpeg_hw_accel else f"Software ({hw.ffmpeg_threads} threads)"

    gr.Markdown(
        "# 🎬 TikTok Voice Generator\n"
        "**100% automatisé** — Tape ton texte, donne ta voix, clique. C'est tout.\n\n"
        "`Texte → Pexels (fond auto) → Chatterbox (voix) → Whisper (sous-titres) → FFmpeg (vidéo)`\n\n"
        f"**Hardware** : {_gpu_info} | Encodage : {_enc_info} | CPU : {hw.cpu_threads} threads"
    )

    with gr.Row():
        with gr.Column(scale=1):
            text_input = gr.Textbox(
                label="📝 Texte à dire",
                placeholder="Tape le texte de ta vidéo ici...",
                lines=5,
            )
            voice_sample = gr.Audio(
                label="🎙️ Ta voix (3-15 secondes)",
                type="filepath",
                sources=["upload", "microphone"],
            )
            language = gr.Dropdown(
                label="🌍 Langue",
                choices=[
                    ("Français", "fr"), ("English", "en"), ("Español", "es"),
                    ("Deutsch", "de"), ("Italiano", "it"), ("Português", "pt"),
                    ("日本語", "ja"), ("中文", "zh"), ("한국어", "ko"), ("العربية", "ar"),
                ],
                value="fr",
            )

            # Section fond automatique
            gr.Markdown("### 🖼️ Fond de la vidéo")
            auto_background = gr.Checkbox(
                label="🔍 Fond automatique (Pexels API)",
                value=media_fetcher.is_available,
                info="Cherche automatiquement des visuels en rapport avec ton texte" if media_fetcher.is_available
                    else "⚠️ Configure PEXELS_API_KEY pour activer (gratuit sur pexels.com/api)",
            )
            prefer_video_bg = gr.Checkbox(
                label="🎥 Préférer les vidéos aux images",
                value=True,
                visible=media_fetcher.is_available,
            )
            manual_background = gr.Image(
                label="📤 Ou : uploader un fond manuellement",
                type="filepath",
            )

            with gr.Accordion("⚙️ Paramètres avancés", open=False):
                subtitle_style = gr.Radio(
                    ["TikTok (2 mots)", "Classique (phrase)"],
                    label="Style sous-titres", value="TikTok (2 mots)",
                )
                font_size = gr.Slider(16, 48, value=28, step=2, label="Taille police")
                exaggeration = gr.Slider(
                    0.0, 1.5, value=0.6, step=0.1,
                    label="Expressivité voix",
                    info="0=monotone, 0.6=normal, 1.2=très expressif",
                )
                cfg_weight = gr.Slider(
                    0.1, 1.0, value=0.5, step=0.1,
                    label="Fidélité au texte",
                    info="Bas=naturel, Haut=fidèle",
                )
                bg_color = gr.ColorPicker(
                    label="Couleur de fond (si pas de média)", value="#1a1a2e",
                )

            generate_btn = gr.Button("🚀 Générer la vidéo", variant="primary", size="lg")

        with gr.Column(scale=1):
            video_output = gr.Video(label="📱 Résultat")
            status_output = gr.Textbox(label="📊 Statut", interactive=False)

    generate_btn.click(
        fn=generate_video,
        inputs=[
            text_input, voice_sample, language,
            auto_background, manual_background, prefer_video_bg,
            subtitle_style, font_size, exaggeration, cfg_weight, bg_color,
        ],
        outputs=[video_output, status_output],
    )

    gr.Markdown(
        "### 💡 Conseils\n"
        "- **Voix** : 5-15s, sans bruit de fond, parle naturellement\n"
        "- **Expressivité** : 0.6-0.8 pour un ton TikTok dynamique\n"
        "- **Fond auto** : Crée un compte gratuit sur [pexels.com/api](https://www.pexels.com/api/) "
        "et configure `PEXELS_API_KEY`\n"
        "- **Texte** : 30-60s max pour le format court"
    )


if __name__ == "__main__":
    app.launch(server_name="0.0.0.0", server_port=7860, share=False)
