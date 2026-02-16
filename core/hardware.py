"""
Auto-détection et optimisation matérielle.
Optimisé pour : AMD Ryzen 7 5700X3D + RX 6950 XT + 32GB DDR4-3200.
Supporte ROCm (Linux/AMD), CUDA (NVIDIA), et CPU fallback.
"""
import os
import platform
import subprocess
from dataclasses import dataclass, field


@dataclass
class HardwareProfile:
    """Profil matériel détecté automatiquement."""
    cpu_threads: int = 8
    gpu_available: bool = False
    gpu_backend: str = "cpu"  # "cuda", "rocm", "cpu"
    gpu_name: str = ""
    gpu_vram_mb: int = 0
    ram_total_mb: int = 0
    ffmpeg_hw_accel: str = ""  # "vaapi", "nvenc", ""
    ffmpeg_threads: int = 4
    compute_type: str = "int8"  # pour Faster-Whisper
    torch_dtype: str = "float32"
    system: str = ""

    def summary(self) -> str:
        """Résumé lisible du profil."""
        lines = [
            f"  OS         : {self.system}",
            f"  CPU        : {self.cpu_threads} threads",
            f"  RAM        : {self.ram_total_mb} MB",
            f"  GPU        : {self.gpu_name or 'Non détecté'} ({self.gpu_backend})",
        ]
        if self.gpu_vram_mb:
            lines.append(f"  VRAM       : {self.gpu_vram_mb} MB")
        lines.append(f"  FFmpeg HW  : {self.ffmpeg_hw_accel or 'software'}")
        lines.append(f"  FFmpeg CPU : {self.ffmpeg_threads} threads")
        lines.append(f"  Compute    : {self.compute_type}")
        lines.append(f"  Torch      : {self.torch_dtype}")
        return "\n".join(lines)


def detect_hardware() -> HardwareProfile:
    """Détecte automatiquement le matériel et optimise les paramètres."""
    profile = HardwareProfile()
    profile.system = f"{platform.system()} {platform.release()}"

    # CPU threads
    profile.cpu_threads = os.cpu_count() or 8
    # FFmpeg utilise ~75% des threads pour laisser de la marge au système
    profile.ffmpeg_threads = max(2, int(profile.cpu_threads * 0.75))

    # RAM
    profile.ram_total_mb = _detect_ram()

    # GPU : tester ROCm d'abord (AMD), puis CUDA (NVIDIA)
    _detect_gpu(profile)

    # Optimiser compute_type selon le matériel
    if profile.gpu_backend == "cuda":
        profile.compute_type = "float16"
        profile.torch_dtype = "float16"
    elif profile.gpu_backend == "rocm":
        # Faster-Whisper (CTranslate2) ne supporte pas bien ROCm
        # → on garde le CPU pour Whisper, GPU pour Chatterbox (PyTorch)
        profile.compute_type = "int8"
        profile.torch_dtype = "float16"
    else:
        profile.compute_type = "int8"
        profile.torch_dtype = "float32"

    # FFmpeg hardware acceleration
    _detect_ffmpeg_hw(profile)

    return profile


def _detect_ram() -> int:
    """Détecte la RAM totale en MB."""
    try:
        if platform.system() == "Linux":
            with open("/proc/meminfo") as f:
                for line in f:
                    if line.startswith("MemTotal:"):
                        return int(line.split()[1]) // 1024
        elif platform.system() == "Windows":
            import ctypes
            kernel32 = ctypes.windll.kernel32
            c_ulonglong = ctypes.c_ulonglong
            class MEMORYSTATUSEX(ctypes.Structure):
                _fields_ = [
                    ("dwLength", ctypes.c_ulong),
                    ("dwMemoryLoad", ctypes.c_ulong),
                    ("ullTotalPhys", c_ulonglong),
                    ("ullAvailPhys", c_ulonglong),
                    ("ullTotalPageFile", c_ulonglong),
                    ("ullAvailPageFile", c_ulonglong),
                    ("ullTotalVirtual", c_ulonglong),
                    ("ullAvailVirtual", c_ulonglong),
                    ("ullAvailExtendedVirtual", c_ulonglong),
                ]
            stat = MEMORYSTATUSEX()
            stat.dwLength = ctypes.sizeof(stat)
            kernel32.GlobalMemoryStatusEx(ctypes.byref(stat))
            return int(stat.ullTotalPhys // (1024 * 1024))
    except Exception:
        pass
    return 0


def _detect_gpu(profile: HardwareProfile) -> None:
    """Détecte le GPU via PyTorch (ROCm ou CUDA)."""
    try:
        import torch

        if torch.cuda.is_available():
            device_name = torch.cuda.get_device_name(0)
            vram = torch.cuda.get_device_properties(0).total_mem // (1024 * 1024)

            # Déterminer si c'est ROCm (AMD) ou CUDA (NVIDIA)
            # PyTorch ROCm expose torch.cuda mais c'est en fait HIP/ROCm
            is_rocm = hasattr(torch.version, "hip") and torch.version.hip is not None

            profile.gpu_available = True
            profile.gpu_name = device_name
            profile.gpu_vram_mb = vram
            profile.gpu_backend = "rocm" if is_rocm else "cuda"
            return

    except ImportError:
        pass

    # Fallback : détecter via rocm-smi (Linux AMD sans PyTorch)
    try:
        result = subprocess.run(
            ["rocm-smi", "--showproductname"],
            capture_output=True, text=True, timeout=5,
        )
        if result.returncode == 0 and "GPU" in result.stdout:
            profile.gpu_available = True
            profile.gpu_backend = "rocm"
            for line in result.stdout.splitlines():
                if "Card" in line or "GPU" in line:
                    profile.gpu_name = line.strip()
                    break
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass


def _detect_ffmpeg_hw(profile: HardwareProfile) -> None:
    """Détecte l'accélération matérielle FFmpeg disponible."""
    try:
        result = subprocess.run(
            ["ffmpeg", "-hwaccels"], capture_output=True, text=True, timeout=5,
        )
        output = result.stdout.lower()

        # AMD : VAAPI sur Linux
        if "vaapi" in output and platform.system() == "Linux":
            # Vérifier que le device VAAPI existe
            if os.path.exists("/dev/dri/renderD128"):
                profile.ffmpeg_hw_accel = "vaapi"
                return

        # NVIDIA : NVENC
        if "nvenc" in output or "cuda" in output:
            profile.ffmpeg_hw_accel = "nvenc"
            return

    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass


# Singleton global — détecté une seule fois
_profile: HardwareProfile | None = None


def get_profile() -> HardwareProfile:
    """Retourne le profil matériel (singleton, détecté une seule fois)."""
    global _profile
    if _profile is None:
        _profile = detect_hardware()
    return _profile
