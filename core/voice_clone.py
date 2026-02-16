"""
Clonage vocal avec Chatterbox Multilingual (Resemble AI).
Supporte 23 langues dont le français. MIT License.
"""
import torch
import torchaudio as ta
from pathlib import Path


class VoiceCloner:
    """Clone une voix à partir d'un échantillon audio de 3-15 secondes."""

    SUPPORTED_LANGUAGES = [
        "ar", "da", "de", "el", "en", "es", "fi", "fr", "he", "hi",
        "it", "ja", "ko", "ms", "nl", "no", "pl", "pt", "ru", "sv",
        "sw", "tr", "zh",
    ]

    def __init__(self, device: str = "auto"):
        if device == "auto":
            self.device = "cuda" if torch.cuda.is_available() else "cpu"
        else:
            self.device = device
        self._model = None

    @property
    def model(self):
        """Lazy loading du modèle Chatterbox Multilingual."""
        if self._model is None:
            from chatterbox.tts import ChatterboxMultilingualTTS
            print(f"⏳ Chargement Chatterbox Multilingual ({self.device})...")
            self._model = ChatterboxMultilingualTTS.from_pretrained(device=self.device)
            print("✅ Modèle vocal chargé !")
        return self._model

    def generate(
        self,
        text: str,
        voice_sample_path: str,
        output_path: str,
        language: str = "fr",
        exaggeration: float = 0.5,
        cfg_weight: float = 0.5,
    ) -> str:
        """
        Génère un audio avec la voix clonée.

        Args:
            text: Texte à synthétiser
            voice_sample_path: Échantillon audio de référence (3-15s, WAV)
            output_path: Chemin de sortie (.wav)
            language: Code ISO langue (fr, en, es, de...)
            exaggeration: Expressivité (0.0=monotone → 1.5=très expressif)
            cfg_weight: Fidélité texte (0.3=naturel → 0.7=fidèle)

        Returns:
            Chemin du fichier audio généré
        """
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        print(f"🎙️ Génération vocale [{language}] : {text[:60]}...")

        wav = self.model.generate(
            text,
            audio_prompt_path=voice_sample_path,
            language_id=language,
            exaggeration=exaggeration,
            cfg_weight=cfg_weight,
        )

        ta.save(output_path, wav, self.model.sr)
        print(f"✅ Audio : {output_path}")
        return output_path
