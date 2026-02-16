"""
Clonage vocal avec Chatterbox Multilingual (Resemble AI).
Supporte 23 langues dont le français. MIT License.
Optimisé : ROCm (AMD GPU), CUDA (NVIDIA), ou CPU avec gestion mémoire.
"""
import gc

import torch
import torchaudio as ta
from pathlib import Path

from core.hardware import get_profile


class VoiceCloner:
    """Clone une voix à partir d'un échantillon audio de 3-15 secondes."""

    SUPPORTED_LANGUAGES = [
        "ar", "da", "de", "el", "en", "es", "fi", "fr", "he", "hi",
        "it", "ja", "ko", "ms", "nl", "no", "pl", "pt", "ru", "sv",
        "sw", "tr", "zh",
    ]

    def __init__(self, device: str = "auto"):
        hw = get_profile()
        if device == "auto":
            # ROCm et CUDA apparaissent tous deux comme "cuda" via PyTorch
            self.device = "cuda" if hw.gpu_available else "cpu"
        else:
            self.device = device
        self._model = None

    @property
    def model(self):
        """Lazy loading du modèle Chatterbox Multilingual."""
        if self._model is None:
            from chatterbox.tts import ChatterboxMultilingualTTS

            hw = get_profile()
            backend = hw.gpu_backend if hw.gpu_available else "cpu"
            print(f"⏳ Chargement Chatterbox Multilingual ({self.device}, backend={backend})...")

            # Libérer la mémoire GPU avant de charger un gros modèle
            if self.device == "cuda":
                torch.cuda.empty_cache()
                gc.collect()

            self._model = ChatterboxMultilingualTTS.from_pretrained(device=self.device)

            # Optimisation : mode eval + désactiver les gradients
            self._model.eval()

            if hw.gpu_vram_mb >= 12000 and self.device == "cuda":
                # RX 6950 XT a 16GB VRAM → on peut utiliser half precision
                try:
                    self._model.half()
                    print("   → Half precision (float16) activé")
                except Exception:
                    pass  # Certains modules ne supportent pas half

            print(f"✅ Modèle vocal chargé ! (VRAM: {hw.gpu_vram_mb}MB)")
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

        with torch.no_grad():
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

    def unload(self) -> None:
        """Libère le modèle de la mémoire GPU/RAM."""
        if self._model is not None:
            del self._model
            self._model = None
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
            gc.collect()
            print("🗑️ Modèle vocal déchargé")
