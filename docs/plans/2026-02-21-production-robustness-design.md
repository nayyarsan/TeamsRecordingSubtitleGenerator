# Production Robustness Design

**Date:** 2026-02-21
**Status:** Approved

## Goal

Make the application production-ready for CPU-first deployments by removing phantom dependencies, isolating pipeline stage failures with user-readable fallbacks, explicitly handling the zero-faces scenario, and extending environment verification to cover the two most common setup failures.

## Scope

Four targeted changes — no architectural changes, no new features.

---

## Section 1: Remove Phantom Dependencies

**Files:** `requirements.txt`, `setup.py`

Remove `spacy>=3.5.0` and `transformers>=4.30.0`. Both packages are listed as dependencies but are never imported anywhere in `src/`. They add ~500MB to the install and have heavy C/Rust build dependencies that frequently fail on CPU-only machines.

No functional change required — the codebase is unaffected.

---

## Section 2: Pipeline Stage Isolation

**Files:** `src/pipeline.py`

### Current state
One top-level try/except re-raises all exceptions. Individual stages have no isolation. Any unhandled exception surfaces as a raw Python traceback to the frontend.

### Design

Add a `_warn(progress_callback, message)` helper method on `MeetingProcessor` that sends a warning through the existing `progress_callback` mechanism at `level: "warning"`. The frontend already renders log entries with levels — no frontend changes needed.

Wrap each stage call in its own try/except with a **fallback value**:

| Stage | On failure | Fallback value |
|---|---|---|
| Audio extraction (FFmpeg) | Fatal — re-raise with clean message | — |
| Diarization (PyAnnote) | Fatal — re-raise with clean message | — |
| Transcription (Whisper) | Warn + skip | `transcript_segments = []` |
| Video / face detection | Warn + skip | `face_data = []` |
| Fusion | Warn + skip | `fused_segments = diarization_only` |
| Naming | Warn + use defaults | Already handled |
| Output generation | Fatal — re-raise with clean message | — |
| Annotated video | Warn + skip | Already isolated |

**Fatal stages** (audio extraction, diarization, output) cannot produce meaningful output if they fail — they re-raise with a clean, human-readable message instead of a raw traceback.

**Recoverable stages** (transcription, video, fusion) degrade gracefully — the job continues and produces partial output.

### Error message format

Fatal errors sent to frontend: `"Audio extraction failed: FFmpeg not found on PATH. Install FFmpeg and add it to PATH."`
Warnings: `"Face detection failed: MediaPipe error. Continuing without visual speaker data."`

No Python class names, no stack traces in messages shown to the user.

---

## Section 3: Audio-Only Mode Notification

**Files:** `src/pipeline.py`

### Current state
When face detection returns 0 faces across all frames, the pipeline silently continues. Fusion runs on empty data, producing output with no face-speaker associations. The user sees speaker labels but has no explanation for why visual identification didn't work.

### Design

After the video stage completes, check total face count:

```python
total_faces = sum(len(faces) for frame_faces in face_data for faces in frame_faces)
if total_faces == 0:
    self._warn(callback, (
        "No faces were detected in the video. "
        "Speaker identification will rely on audio only — "
        "names will be extracted from the transcript if available."
    ))
    # Skip fusion entirely
    fused_segments = self._audio_only_segments(diarization_segments)
```

`_audio_only_segments()` converts diarization segments directly to `SpeakerSegment` objects without face data. The naming and output stages receive these and produce a valid SRT/JSON — just without face-speaker visual associations.

This saves CPU time (skips fusion computation) and gives the user a clear explanation.

---

## Section 4: Extend `verify_environment.py`

**Files:** `verify_environment.py`

### Current state
Checks Python packages and API instantiation. Does not check FFmpeg (required for all processing) or `HF_TOKEN` (required for PyAnnote model download).

### Design

Add two new checks in the existing table format:

**FFmpeg check:**
```
[FAIL] ffmpeg: not found on PATH
       Install: winget install ffmpeg  (Windows)
                brew install ffmpeg    (macOS)
                sudo apt install ffmpeg (Ubuntu)
       Then restart your terminal and re-run this script.
```

**HF_TOKEN check:**
```
[WARN] HF_TOKEN: environment variable not set
       PyAnnote Audio requires a HuggingFace token for gated models.
       1. Accept model licenses at https://huggingface.co/pyannote/speaker-diarization-3.1
       2. Create a token at https://huggingface.co/settings/tokens
       3. Set: $env:HF_TOKEN = 'hf_...'  (Windows PowerShell)
              export HF_TOKEN='hf_...'   (macOS/Linux)
```

HF_TOKEN is a WARN not FAIL because public models work without it. FFmpeg is a FAIL because nothing works without it.

The script's exit code stays 0 for warnings, 1 for failures — no change to the existing behavior contract.

---

## Files Changed

| File | Change |
|---|---|
| `requirements.txt` | Remove `spacy`, `transformers` |
| `setup.py` | Remove `spacy`, `transformers` from install_requires |
| `src/pipeline.py` | Add `_warn()`, `_audio_only_segments()`, wrap each stage |
| `verify_environment.py` | Add FFmpeg and HF_TOKEN checks |

## Out of Scope

- No frontend changes
- No new API endpoints
- No model changes (Whisper stays at `base` — user can set `tiny` in config.yaml)
- No Docker / containerization
- No authentication or access control
