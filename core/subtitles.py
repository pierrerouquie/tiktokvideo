"""
Génération de sous-titres avec Faster-Whisper (large-v3).
Produit des fichiers SRT avec timestamps mot par mot.
"""
from faster_whisper import WhisperModel
from pathlib import Path


class SubtitleGenerator:
    """Transcrit un audio en sous-titres SRT synchronisés."""

    def __init__(self, model_size: str = "large-v3", device: str = "auto"):
        """
        Args:
            model_size: "large-v3" (meilleur), "medium", "small" (rapide)
            device: "cuda", "cpu", ou "auto"
        """
        if device == "auto":
            import torch
            compute_type = "float16" if torch.cuda.is_available() else "int8"
            device = "cuda" if torch.cuda.is_available() else "cpu"
        else:
            compute_type = "float16" if device == "cuda" else "int8"

        print(f"⏳ Chargement Faster-Whisper ({model_size}, {device})...")
        self.model = WhisperModel(model_size, device=device, compute_type=compute_type)
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
            audio_path, language=language, word_timestamps=True,
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
