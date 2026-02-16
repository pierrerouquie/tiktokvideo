# TikTok Voice Generator

Automated short-video pipeline: Text → Voice Clone → Subtitles → Video.

## Stack

- Python 3.11, Chatterbox TTS v0.1.6+ with Turbo mode (voice cloning), Faster-Whisper 1.2+ with large-v3-turbo (STT), FFmpeg (video), Pexels + Pixabay APIs (stock footage)
- Interface: Gradio 6+
- GPU: NVIDIA CUDA / AMD ROCm 7.x (fallback CPU for non-GPU tasks)

## Commands

```bash
# Install
pip install -r requirements.txt

# Run web UI
python app.py

# Run CLI
python cli.py -t "Mon texte" -v assets/voices/sample.wav

# Run tests
python -m pytest tests/ -v

# Type check
python -m mypy core/ --ignore-missing-imports

# Lint
python -m ruff check core/ app.py cli.py
```

## Code Style

- Python 3.11+ with type hints on all function signatures
- Docstrings: Google style, French comments OK
- Imports: stdlib → third-party → local, separated by blank lines
- Classes for modules (`VoiceCloner`, `SubtitleGenerator`, `VideoMaker`, `MediaFetcher`)
- Lazy loading for heavy models (load on first use, not import)
- Error handling: catch specific exceptions, log with print emoji prefixes (⏳🎙️📝🎬✅❌)
- All file paths as `str`, use `pathlib.Path` internally

## Architecture

```
core/
  voice_clone.py   → VoiceCloner (Chatterbox Turbo/Multilingual)
  subtitles.py     → SubtitleGenerator (Faster-Whisper large-v3-turbo)
  video_maker.py   → VideoMaker (FFmpeg subprocess)
  media_fetcher.py → MediaFetcher (Pexels + Pixabay APIs + keyword extraction)
app.py             → Gradio web interface
cli.py             → CLI entry point
```

## Workflow

1. Read existing code before making changes
2. Make small, focused edits — one module at a time
3. Test after each change: `python -c "from core.module import Class; print('OK')"`
4. Keep CLAUDE.md updated if architecture changes
5. Commit after each working feature

## Key Decisions

- Pexels API (primary) + Pixabay API (fallback) for automated stock footage (both free)
- Fallback to solid color background if both APIs fail or no API keys
- Chatterbox-Turbo mode by default (350M params, 1-step decoder, faster) with quality mode available
- Faster-Whisper large-v3-turbo by default (6x faster than large-v3, ~1-2% less accurate)
- SRT subtitles with word-level timestamps for TikTok style
- Output format: 1080x1920 (9:16 vertical), H.264, AAC audio
- All processing local except Pexels/Pixabay HTTP calls
- PyTorch with ROCm 7.x (AMD) or CUDA 12.x (NVIDIA) support
