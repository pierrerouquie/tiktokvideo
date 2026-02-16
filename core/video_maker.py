"""
Assemblage vidéo avec FFmpeg.
Supporte : fond vidéo (loop), fond image (Ken Burns zoom/pan), fond uni.
Format de sortie : 1080x1920 (9:16 TikTok), H.264 + AAC.
Optimisé : multi-threading FFmpeg (12 threads Ryzen 7 5700X3D),
           VAAPI hardware encoding sur Linux/AMD, NVENC sur NVIDIA.
"""
import subprocess
import shutil
from pathlib import Path

from core.hardware import get_profile


class VideoMaker:
    """Assemble audio + sous-titres + fond en vidéo TikTok."""

    WIDTH = 1080
    HEIGHT = 1920

    def __init__(self):
        if not shutil.which("ffmpeg"):
            raise RuntimeError(
                "FFmpeg non trouvé ! Installe-le :\n"
                "  Ubuntu: sudo apt install ffmpeg\n"
                "  Mac: brew install ffmpeg\n"
                "  Windows: choco install ffmpeg"
            )
        self._hw = get_profile()

    def _encoding_args(self) -> list[str]:
        """Paramètres d'encodage optimisés selon le hardware détecté."""
        hw = self._hw

        if hw.ffmpeg_hw_accel == "vaapi":
            # AMD RX 6950 XT VAAPI : encodage hardware H.264
            return [
                "-vaapi_device", "/dev/dri/renderD128",
                "-vf", "format=nv12,hwupload",
                "-c:v", "h264_vaapi",
                "-qp", "23",
            ]
        elif hw.ffmpeg_hw_accel == "nvenc":
            # NVIDIA NVENC
            return [
                "-c:v", "h264_nvenc",
                "-preset", "p4",
                "-cq", "23",
            ]
        else:
            # CPU software encoding — optimisé multi-thread
            return [
                "-c:v", "libx264",
                "-preset", "fast",
                "-crf", "23",
                "-threads", str(hw.ffmpeg_threads),
            ]

    def create(
        self,
        audio_path: str,
        srt_path: str,
        output_path: str,
        background_path: str = "",
        background_type: str = "auto",
        bg_color: str = "#1a1a2e",
        font_size: int = 28,
        font_color: str = "white",
        outline_color: str = "black",
        outline_width: int = 3,
        sub_position: str = "center",
    ) -> str:
        """
        Crée une vidéo TikTok complète.

        Args:
            audio_path: Fichier audio (.wav)
            srt_path: Fichier sous-titres (.srt)
            output_path: Fichier de sortie (.mp4)
            background_path: Vidéo ou image de fond (vide = fond uni)
            background_type: "video", "image", "auto" (détecte), ou "none" (fond uni)
            bg_color: Couleur hex du fond uni (#1a1a2e)
            font_size: Taille police sous-titres
            font_color: Couleur texte (nom CSS ou hex)
            outline_color: Couleur contour texte
            outline_width: Épaisseur contour
            sub_position: "center", "bottom", "top"

        Returns:
            Chemin de la vidéo générée
        """
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        duration = self._get_duration(audio_path)

        # Détecter le type de fond
        if background_type == "auto":
            background_type = self._detect_bg_type(background_path)

        # Construire le filtre sous-titres ASS
        srt_escaped = srt_path.replace("\\", "/").replace(":", "\\:")
        sub_filter = (
            f"subtitles='{srt_escaped}'"
            f":force_style='FontSize={font_size}"
            f",PrimaryColour=&H00{self._to_bgr(font_color)}"
            f",OutlineColour=&H00{self._to_bgr(outline_color)}"
            f",Outline={outline_width}"
            f",Alignment={self._alignment(sub_position)}"
            f",MarginV=100,Bold=1'"
        )

        # Construire la commande selon le type de fond
        if background_type == "video":
            cmd = self._cmd_video_bg(background_path, audio_path, sub_filter, duration, output_path)
        elif background_type == "image":
            cmd = self._cmd_image_bg(background_path, audio_path, sub_filter, duration, output_path)
        else:
            cmd = self._cmd_color_bg(bg_color, audio_path, sub_filter, duration, output_path)

        hw = self._hw
        enc_info = hw.ffmpeg_hw_accel or f"software {hw.ffmpeg_threads}t"
        print(f"🎬 Assemblage vidéo ({background_type}, {enc_info}) — {duration:.1f}s...")
        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode != 0:
            # Fallback vers encodage software si le hardware échoue
            if hw.ffmpeg_hw_accel:
                print(f"⚠️ Encodage hardware ({hw.ffmpeg_hw_accel}) échoué, fallback software...")
                hw.ffmpeg_hw_accel = ""
                if background_type == "video":
                    cmd = self._cmd_video_bg(background_path, audio_path, sub_filter, duration, output_path)
                elif background_type == "image":
                    cmd = self._cmd_image_bg(background_path, audio_path, sub_filter, duration, output_path)
                else:
                    cmd = self._cmd_color_bg(bg_color, audio_path, sub_filter, duration, output_path)
                result = subprocess.run(cmd, capture_output=True, text=True)

            if result.returncode != 0:
                raise RuntimeError(f"FFmpeg erreur :\n{result.stderr[-500:]}")

        size_mb = Path(output_path).stat().st_size / (1024 * 1024)
        print(f"✅ Vidéo : {output_path} ({size_mb:.1f} Mo)")
        return output_path

    # ── Commandes FFmpeg par type de fond ──────────────────────────────

    def _cmd_video_bg(self, bg: str, audio: str, subs: str, dur: float, out: str) -> list[str]:
        """Fond vidéo : loop + crop + sous-titres."""
        enc = self._encoding_args()
        return [
            "ffmpeg", "-y",
            "-stream_loop", "-1", "-i", bg,
            "-i", audio,
            "-filter_complex",
            f"[0:v]scale={self.WIDTH}:{self.HEIGHT}:force_original_aspect_ratio=increase,"
            f"crop={self.WIDTH}:{self.HEIGHT},"
            f"{subs}[v]",
            "-map", "[v]", "-map", "1:a",
            *enc,
            "-c:a", "aac", "-b:a", "192k",
            "-shortest", "-t", str(dur),
            out,
        ]

    def _cmd_image_bg(self, bg: str, audio: str, subs: str, dur: float, out: str) -> list[str]:
        """Fond image : Ken Burns (zoom progressif) + sous-titres."""
        fps = 30
        total_frames = int(dur * fps)
        enc = self._encoding_args()
        return [
            "ffmpeg", "-y",
            "-loop", "1", "-i", bg,
            "-i", audio,
            "-filter_complex",
            f"[0:v]scale=2160:3840,zoompan=z='min(zoom+0.0003,1.15)'"
            f":x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'"
            f":d={total_frames}:s={self.WIDTH}x{self.HEIGHT}:fps={fps},"
            f"{subs}[v]",
            "-map", "[v]", "-map", "1:a",
            *enc,
            "-c:a", "aac", "-b:a", "192k",
            "-shortest", "-t", str(dur),
            out,
        ]

    def _cmd_color_bg(self, color: str, audio: str, subs: str, dur: float, out: str) -> list[str]:
        """Fond uni coloré."""
        color_clean = color.lstrip("#")
        enc = self._encoding_args()
        return [
            "ffmpeg", "-y",
            "-f", "lavfi",
            "-i", f"color=c=0x{color_clean}:s={self.WIDTH}x{self.HEIGHT}:d={dur}:r=30",
            "-i", audio,
            "-filter_complex", f"[0:v]{subs}[v]",
            "-map", "[v]", "-map", "1:a",
            *enc,
            "-c:a", "aac", "-b:a", "192k",
            "-shortest",
            out,
        ]

    # ── Utilitaires ────────────────────────────────────────────────────

    def _get_duration(self, audio_path: str) -> float:
        """Durée audio via ffprobe."""
        result = subprocess.run(
            ["ffprobe", "-v", "quiet", "-show_entries", "format=duration",
             "-of", "csv=p=0", audio_path],
            capture_output=True, text=True,
        )
        return float(result.stdout.strip())

    @staticmethod
    def _detect_bg_type(path: str) -> str:
        """Détecte le type de fond à partir de l'extension."""
        if not path or not Path(path).exists():
            return "none"
        ext = Path(path).suffix.lower()
        if ext in {".mp4", ".mov", ".avi", ".webm", ".mkv"}:
            return "video"
        if ext in {".jpg", ".jpeg", ".png", ".webp", ".bmp"}:
            return "image"
        return "none"

    @staticmethod
    def _to_bgr(color: str) -> str:
        """Convertit hex/nom CSS → BGR pour ASS. Supporte #RRGGBB et noms."""
        color_map = {
            "white": "FFFFFF", "black": "000000", "red": "0000FF",
            "green": "00FF00", "blue": "FF0000", "yellow": "00FFFF",
        }
        if color.lower() in color_map:
            return color_map[color.lower()]
        h = color.lstrip("#")
        if len(h) == 6:
            return f"{h[4:6]}{h[2:4]}{h[0:2]}"
        return "FFFFFF"

    @staticmethod
    def _alignment(pos: str) -> int:
        """Code alignement ASS."""
        return {"bottom": 2, "center": 5, "top": 8}.get(pos, 5)
