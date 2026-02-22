# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Offline Python tool that identifies and labels speakers in Webex meeting recordings using audio diarization (PyAnnote Audio) + video face detection (MediaPipe). Privacy-first: all processing is local, no external APIs by default.

## Common Commands

### Install
```bash
pip install -e ".[dev]"        # Dev install with test/lint tools
pip install -e ".[llm]"        # With OpenAI/Anthropic support (optional)
```

### Lint (matches CI)
```bash
black --check src/
flake8 src/ --max-line-length=100 --extend-ignore=E203,W503,W293,E501
mypy src/ --ignore-missing-imports
```

### Format
```bash
black src/
```

### Test
```bash
pytest --cov=src --cov-report=xml    # All tests
pytest tests/test_foo.py             # Single file
pytest tests/test_foo.py::test_bar   # Single test
python verify_project.py             # Verify installation

# E2E smoke tests (frontend)
cd frontend && npm run test:e2e      # Launches Vite + runs Playwright
```
Note: test suite is not yet implemented; `tests/` directory needs to be created.

### Run
```bash
# CLI
python process_meeting.py --video VIDEO --output-dir DIR [--transcribe] [--annotate]

# FastAPI server (serves React frontend)
python run_server.py              # port 8000
```

### Frontend (frontend/)
```bash
npm run dev      # Vite dev server
npm run build    # Production build
```

## Architecture

The pipeline processes a video through 6 sequential stages, orchestrated by `MeetingProcessor` in `src/pipeline.py`:

1. **Audio** (`src/audio/processor.py`) — Extract audio via FFmpeg, diarize with PyAnnote Audio, optionally transcribe with Whisper
2. **Video** (`src/video/processor.py`) — Sample frames at 3 FPS, detect faces with MediaPipe, track across frames, detect lip movement
3. **Fusion** (`src/fusion/processor.py`) — Align speaker segments with face detections, score face-speaker associations
4. **Naming** (`src/naming/extractor.py`) — Extract names from intro segments via regex patterns; optionally use local LLM (Ollama) for better extraction
5. **Output** (`src/output/generator.py`) — Generate labeled SRT subtitles and JSON metadata
6. **Visualization** (`src/visualizer.py`) — Optional annotated video with speaker labels

### Two Web UIs
- **Legacy**: Flask-based viewer in `src/web_ui.py`, launched via `view_videos.py`
- **Current**: FastAPI backend (`src/api.py`) + React/Vite/Tailwind frontend (`frontend/`), launched via `run_server.py`

### LLM Integration
`src/llm/ollama.py` provides a lightweight Ollama REST client (stdlib only, no dependencies) for LLM-assisted name extraction. Controlled via `config.yaml` under `naming.llm`.

## Configuration

`config.yaml` controls all processing parameters: audio sample rate, video FPS, fusion thresholds, naming patterns, Whisper model size, LLM settings, and privacy flags.

## Code Style

- **Formatter**: black
- **Linting**: flake8 (max line length 100)
- **Type checking**: mypy
- **Docstrings**: Google-style
- **Python**: 3.8+ compatible

## System Dependency

FFmpeg must be installed and available on PATH.
