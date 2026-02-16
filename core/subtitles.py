"""
Génération de sous-titres avec Faster-Whisper (large-v3).
Produit des fichiers SRT avec timestamps mot par mot.
Optimisé : utilise tous les threads CPU (Ryzen 7 5700X3D = 16 threads).
Note : CTranslate2 (backend de Faster-Whisper) ne supporte pas ROCm,
       donc on utilise le CPU avec int8 quantization + multi-threading.
"""
from faster_whisper import WhisperModel
from pathlib import Path

from core.hardware import get_profile


class SubtitleGenerator:
    """Transcrit un audio en sous-titres SRT synchronisés."""

    def __init__(self, model_size: str = "large-v3", device: str = "auto"):
        """
        Args:
            model_size: "large-v3" (meilleur), "medium", "small" (rapide)
            device: "cuda", "cpu", ou "auto"
        """
        hw = get_profile()

        if device == "auto":
            # CTranslate2 supporte CUDA (NVIDIA) mais PAS ROCm (AMD)
            # Pour AMD GPU (RX 6950 XT) → forcer CPU avec max threads
            if hw.gpu_backend == "cuda":
                device = "cuda"
                compute_type = "float16"
                cpu_threads = 0  # Géré par CUDA
            else:
                device = "cpu"
                compute_type = "int8"
                # Ryzen 7 5700X3D : 8 cores / 16 threads, 96MB L3
                # int8 + multi-thread = très rapide sur ce CPU
                cpu_threads = hw.cpu_threads
        else:
            compute_type = "float16" if device == "cuda" else "int8"
            cpu_threads = hw.cpu_threads if device == "cpu" else 0

        print(f"⏳ Chargement Faster-Whisper ({model_size}, {device}, {compute_type})...")
        if device == "cpu":
            print(f"   → {cpu_threads} threads CPU, int8 quantization")

        self.model = WhisperModel(
            model_size,
            device=device,
            compute_type=compute_type,
            cpu_threads=cpu_threads,
        )
        print("✅ Modèle Whisper chargé !")

    def generate_srt(
        self,
        audio_path: str,
        output_path: str,
        language: str = "fr",
        style: str = "tiktok",
    ) -> str:
        """
        Transcrit un audio en fichier SRT.

        Args:
            audio_path: Fichier audio source
            output_path: Fichier SRT de sortie
            language: Langue de l'audio
            style: "tiktok" (2 mots max, gros texte) ou "classic" (phrase entière)

        Returns:
            Chemin du fichier SRT
        """
        words_per_group = 2 if style == "tiktok" else 8

        print(f"📝 Transcription [{style}] : {audio_path}...")
        segments, _ = self.model.transcribe(
            audio_path,
            language=language,
            word_timestamps=True,
            beam_size=5,
            vad_filter=True,
        )

        srt_entries = []
        index = 1
        buffer: list = []

        for segment in segments:
            if segment.words is None:
                continue
            for word in segment.words:
                buffer.append(word)
                if len(buffer) >= words_per_group:
                    srt_entries.append(self._format_entry(index, buffer))
                    index += 1
                    buffer = []

        if buffer:
            srt_entries.append(self._format_entry(index, buffer))

        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        Path(output_path).write_text("\n".join(srt_entries), encoding="utf-8")
        print(f"✅ Sous-titres : {output_path} ({index} entrées)")
        return output_path

    @staticmethod
    def _ts(seconds: float) -> str:
        """Secondes → timestamp SRT (HH:MM:SS,mmm)."""
        h = int(seconds // 3600)
        m = int((seconds % 3600) // 60)
        s = int(seconds % 60)
        ms = int((seconds % 1) * 1000)
        return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"

    def _format_entry(self, index: int, words: list) -> str:
        """Crée une entrée SRT à partir d'une liste de mots Whisper."""
        start = self._ts(words[0].start)
        end = self._ts(words[-1].end)
        text = " ".join(w.word.strip() for w in words)
        return f"{index}\n{start} --> {end}\n{text}\n"
