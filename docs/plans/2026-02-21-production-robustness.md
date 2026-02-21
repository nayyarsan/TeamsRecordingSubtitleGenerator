# Production Robustness Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Remove unused heavy dependencies, isolate pipeline stage failures with user-readable fallbacks, notify users when no faces are detected, and extend environment verification to catch the two most common setup failures.

**Architecture:** Four targeted changes with no architectural shifts. `pipeline.py` gets a `_warn()` helper and per-stage try/except blocks. `api.py`'s progress callback is updated to forward the `level` field so warnings reach the frontend. `verify_environment.py` grows two new helper functions. Phantom deps are removed from `requirements.txt` and `setup.py`.

**Tech Stack:** Python stdlib only — `shutil`, `os`, `unittest.mock` for tests. No new dependencies.

---

### Task 1: Remove phantom dependencies

**Files:**
- Modify: `requirements.txt`
- Modify: `setup.py`
- Test: `tests/llm/test_clients.py` (existing — verify nothing broke)

**Step 1: Remove from `requirements.txt`**

Delete these two lines from `requirements.txt`:
```
transformers>=4.30.0
spacy>=3.5.0
```

The file currently has them at lines 25–26. After removal, the ML/NLP section should be gone entirely.

**Step 2: Remove from `setup.py`**

Delete these two lines from `setup.py` `install_requires` list (lines 46–47):
```python
        "transformers>=4.30.0",
        "spacy>=3.5.0",
```

**Step 3: Run existing tests to confirm nothing broke**

```bash
python -m pytest tests/ -v
```

Expected: 12 passed.

**Step 4: Commit**

```bash
git add requirements.txt setup.py
git commit -m "chore: remove unused spacy and transformers dependencies"
```

---

### Task 2: Add `_warn()` helper and fix level forwarding

**Files:**
- Modify: `src/pipeline.py` (add `_warn()`, update `_update_progress()`)
- Modify: `src/api.py` (update `progress_cb` to accept and use `level`)
- Test: `tests/test_pipeline_robustness.py` (new)

**Step 1: Write failing tests**

Create `tests/test_pipeline_robustness.py`:

```python
"""Tests for pipeline robustness additions."""

import pytest


def test_warn_logs_entry_at_warning_level():
    from src.pipeline import MeetingProcessor

    proc = MeetingProcessor()
    proc.current_step = "testing"
    proc.current_percent = 42
    proc._warn("something went wrong")

    warning_entries = [
        log for log in proc.log_buffer if log.get("level") == "warning"
    ]
    assert len(warning_entries) == 1
    assert "something went wrong" in warning_entries[0]["message"]


def test_update_progress_passes_level_to_callback():
    from src.pipeline import MeetingProcessor

    received = []

    def cb(step, pct, msg, level="info"):
        received.append(level)

    proc = MeetingProcessor(progress_callback=cb)
    proc._update_progress("step", 10, "msg", level="warning")
    assert received == ["warning"]


def test_count_total_faces_returns_zero_for_empty_list():
    from src.pipeline import MeetingProcessor

    proc = MeetingProcessor()
    assert proc._count_total_faces([]) == 0


def test_count_total_faces_sums_across_frames():
    from src.pipeline import MeetingProcessor

    proc = MeetingProcessor()
    # frame_data_list: list of frames, each frame is a list of face detections
    frame_data = [["face1", "face2"], [], ["face3"]]
    assert proc._count_total_faces(frame_data) == 3
```

**Step 2: Run tests to confirm they fail**

```bash
python -m pytest tests/test_pipeline_robustness.py -v
```

Expected: `AttributeError: 'MeetingProcessor' object has no attribute '_warn'`

**Step 3: Add `_warn()` and `_count_total_faces()` to `src/pipeline.py`**

In `src/pipeline.py`, find the `get_progress()` method (ends around line 83). Add these two methods immediately after it:

```python
    def _warn(self, message: str) -> None:
        """Send a warning-level message through the progress callback."""
        self._update_progress(self.current_step, self.current_percent, message, level="warning")

    def _count_total_faces(self, frame_data_list: list) -> int:
        """Count total face detections across all frames."""
        return sum(len(frame_faces) for frame_faces in frame_data_list)
```

**Step 4: Update `_update_progress()` to forward `level` to the callback**

Find this line in `_update_progress()` (around line 73):

```python
            self._progress_callback(step, percent, message)
```

Replace with:

```python
            self._progress_callback(step, percent, message, level)
```

**Step 5: Update `progress_cb` in `src/api.py`**

In `src/api.py`, inside `_run_processing()`, find:

```python
        def progress_cb(step, percent, message):
            if video_id in _jobs:
                _jobs[video_id]["step"] = step
                _jobs[video_id]["percent"] = percent
                _jobs[video_id]["logs"].append({
                    "step": step, "percent": percent,
                    "message": message, "level": "info",
                })
```

Replace with:

```python
        def progress_cb(step, percent, message, level="info"):
            if video_id in _jobs:
                _jobs[video_id]["step"] = step
                _jobs[video_id]["percent"] = percent
                _jobs[video_id]["logs"].append({
                    "step": step, "percent": percent,
                    "message": message, "level": level,
                })
```

**Step 6: Run all tests**

```bash
python -m pytest tests/ -v
```

Expected: 16 passed (12 existing + 4 new).

**Step 7: Lint**

```bash
black src/pipeline.py src/api.py
flake8 src/pipeline.py src/api.py --max-line-length=100 --extend-ignore=E203,W503,W293,E501
```

**Step 8: Commit**

```bash
git add src/pipeline.py src/api.py tests/test_pipeline_robustness.py
git commit -m "feat: add _warn helper and forward level through progress callback"
```

---

### Task 3: Pipeline stage isolation

**Files:**
- Modify: `src/pipeline.py` (wrap transcription, video, fusion stages)
- Test: `tests/test_pipeline_robustness.py` (add tests for zero-face warning)

**Step 1: Add zero-face test to `tests/test_pipeline_robustness.py`**

Append to the file:

```python
def test_warn_is_called_when_no_faces_detected():
    """_count_total_faces with all-empty frame lists returns 0."""
    from src.pipeline import MeetingProcessor

    proc = MeetingProcessor()
    # Simulate frame data where MediaPipe found nothing in any frame
    frame_data_all_empty = [[], [], [], []]
    assert proc._count_total_faces(frame_data_all_empty) == 0
```

**Step 2: Run to confirm it passes (it should, since `_count_total_faces` is already implemented)**

```bash
python -m pytest tests/test_pipeline_robustness.py::test_warn_is_called_when_no_faces_detected -v
```

Expected: PASS.

**Step 3: Wrap transcription stage in `src/pipeline.py`**

Find the transcription block in `process()` (lines ~151–165):

```python
            # Step 2: Parse transcript
            self._update_progress("transcription", 20, "Parsing transcript...")
            logger.info("\n[2/6] Parsing transcript...")
            if transcript_path:
                transcript_segments = TranscriptParser.parse(transcript_path)
            else:
                transcription_config = self.config.get("transcription", default={})
                model_size = asr_model or transcription_config.get("model", "base")
                language = asr_language or transcription_config.get("language")
                logger.info(
                    f"Auto-transcribing audio using Whisper model: {model_size}"
                )
                transcript_segments = TranscriptParser.transcribe_audio(
                    audio_path, model_size=model_size, language=language
                )
            logger.info(f"Transcript parsed: {len(transcript_segments)} segments")
```

Replace with:

```python
            # Step 2: Parse transcript
            self._update_progress("transcription", 20, "Parsing transcript...")
            logger.info("\n[2/6] Parsing transcript...")
            try:
                if transcript_path:
                    transcript_segments = TranscriptParser.parse(transcript_path)
                else:
                    transcription_config = self.config.get("transcription", default={})
                    model_size = asr_model or transcription_config.get("model", "base")
                    language = asr_language or transcription_config.get("language")
                    logger.info(
                        f"Auto-transcribing audio using Whisper model: {model_size}"
                    )
                    transcript_segments = TranscriptParser.transcribe_audio(
                        audio_path, model_size=model_size, language=language
                    )
                logger.info(f"Transcript parsed: {len(transcript_segments)} segments")
            except Exception as e:
                self._warn(
                    f"Transcription failed: {e}. "
                    "Continuing without transcript text — speaker labels will be generated "
                    "from audio diarization only."
                )
                transcript_segments = []
```

**Step 4: Wrap video/face detection stage in `src/pipeline.py`**

Find the video block (lines ~167–178):

```python
            # Step 3: Process video and detect faces
            self._update_progress("face_detection", 35, "Processing video and detecting faces...")
            logger.info("\n[3/6] Processing video and detecting faces...")
            frame_data_list = self.video_processor.process_video(video_path)

            video_stats = self.video_processor.get_face_statistics()
            logger.info(f"Video processing complete: {len(video_stats)} faces tracked")
            for face_id, stats in video_stats.items():
                logger.info(
                    f"  {face_id}: {stats['duration']:.1f}s "
                    f"({stats['frame_count']} frames)"
                )
```

Replace with:

```python
            # Step 3: Process video and detect faces
            self._update_progress("face_detection", 35, "Processing video and detecting faces...")
            logger.info("\n[3/6] Processing video and detecting faces...")
            try:
                frame_data_list = self.video_processor.process_video(video_path)
                video_stats = self.video_processor.get_face_statistics()
                logger.info(f"Video processing complete: {len(video_stats)} faces tracked")
                for face_id, stats in video_stats.items():
                    logger.info(
                        f"  {face_id}: {stats['duration']:.1f}s "
                        f"({stats['frame_count']} frames)"
                    )
            except Exception as e:
                self._warn(
                    f"Face detection failed: {e}. "
                    "Continuing without visual speaker data."
                )
                frame_data_list = []

            if self._count_total_faces(frame_data_list) == 0 and frame_data_list is not None:
                self._warn(
                    "No faces were detected in the video. Speaker identification will rely on "
                    "audio only — names will be extracted from the transcript if available."
                )
```

**Step 5: Wrap fusion stage in `src/pipeline.py`**

Find the fusion block (lines ~180–196):

```python
            # Step 4: Fuse audio and video
            self._update_progress("fusion", 55, "Fusing audio and video data...")
            logger.info("\n[4/6] Fusing audio and video data...")
            fused_segments = self.fusion_processor.fuse(
                diarization_segments, frame_data_list
            )

            fusion_stats = self.fusion_processor.get_statistics(fused_segments)
            logger.info(
                f"Fusion complete: {fusion_stats['segments_with_faces']}/{fusion_stats['total_segments']} "
                f"segments with faces"
            )

            # Build speaker-face mapping
            speaker_face_mapping = self.fusion_processor.build_speaker_face_mapping(
                fused_segments
            )
```

Replace with:

```python
            # Step 4: Fuse audio and video
            self._update_progress("fusion", 55, "Fusing audio and video data...")
            logger.info("\n[4/6] Fusing audio and video data...")
            try:
                fused_segments = self.fusion_processor.fuse(
                    diarization_segments, frame_data_list
                )
                fusion_stats = self.fusion_processor.get_statistics(fused_segments)
                logger.info(
                    f"Fusion complete: {fusion_stats['segments_with_faces']}/{fusion_stats['total_segments']} "
                    f"segments with faces"
                )
                speaker_face_mapping = self.fusion_processor.build_speaker_face_mapping(
                    fused_segments
                )
            except Exception as e:
                self._warn(
                    f"Audio-visual fusion failed: {e}. "
                    "Falling back to audio-only speaker segments."
                )
                fused_segments = self.fusion_processor.fuse(diarization_segments, [])
                speaker_face_mapping = {}
```

**Step 6: Make audio/output errors human-readable**

Find the outer except block at the end of `process()` (lines ~272–274):

```python
        except Exception as e:
            logger.error(f"Processing failed: {e}", exc_info=True)
            raise
```

Replace with:

```python
        except RuntimeError:
            # Already a clean user-facing message — re-raise as-is
            raise
        except Exception as e:
            logger.error(f"Processing failed: {e}", exc_info=True)
            raise RuntimeError(
                f"Processing failed: {e}. "
                "Check that FFmpeg is installed, HF_TOKEN is set, and the video file is valid."
            ) from e
```

**Step 7: Run all tests**

```bash
python -m pytest tests/ -v
```

Expected: 17 passed.

**Step 8: Lint and format**

```bash
black src/pipeline.py
flake8 src/pipeline.py --max-line-length=100 --extend-ignore=E203,W503,W293,E501
```

**Step 9: Commit**

```bash
git add src/pipeline.py tests/test_pipeline_robustness.py
git commit -m "feat: isolate pipeline stages with graceful fallbacks and zero-face warning"
```

---

### Task 4: Extend `verify_environment.py`

**Files:**
- Modify: `verify_environment.py`
- Test: `tests/test_verify_environment.py` (new)

**Step 1: Write failing tests**

Create `tests/test_verify_environment.py`:

```python
"""Tests for verify_environment helper functions."""

import os
from unittest.mock import patch


def test_check_ffmpeg_returns_true_when_found():
    import verify_environment
    with patch("shutil.which", return_value="/usr/bin/ffmpeg"):
        result = verify_environment.check_ffmpeg()
    assert result is True


def test_check_ffmpeg_returns_false_when_missing():
    import verify_environment
    with patch("shutil.which", return_value=None):
        result = verify_environment.check_ffmpeg()
    assert result is False


def test_check_hf_token_returns_true_when_set():
    import verify_environment
    with patch.dict(os.environ, {"HF_TOKEN": "hf_testtoken"}):
        result = verify_environment.check_hf_token()
    assert result is True


def test_check_hf_token_returns_false_when_missing():
    import verify_environment
    env = {k: v for k, v in os.environ.items() if k != "HF_TOKEN"}
    with patch.dict(os.environ, env, clear=True):
        result = verify_environment.check_hf_token()
    assert result is False
```

**Step 2: Run to confirm they fail**

```bash
python -m pytest tests/test_verify_environment.py -v
```

Expected: `AttributeError: module 'verify_environment' has no attribute 'check_ffmpeg'`

**Step 3: Add `check_ffmpeg()` and `check_hf_token()` to `verify_environment.py`**

Add `import shutil` to the existing imports at the top of `verify_environment.py`:

Find:
```python
import sys
from pathlib import Path
```

Replace with:
```python
import os
import shutil
import sys
from pathlib import Path
```

Then add these two functions immediately after `check_module()` (after line 21):

```python
def check_ffmpeg():
    """Check if ffmpeg is available on PATH."""
    path = shutil.which("ffmpeg")
    if path:
        print(f"  [OK] ffmpeg: found at {path}")
        return True
    else:
        print("  [FAIL] ffmpeg: NOT FOUND on PATH")
        print("         Install:")
        print("           Windows : winget install ffmpeg")
        print("           macOS   : brew install ffmpeg")
        print("           Ubuntu  : sudo apt install ffmpeg")
        print("         Then restart your terminal and re-run this script.")
        return False


def check_hf_token():
    """Check if HF_TOKEN environment variable is set."""
    token = os.environ.get("HF_TOKEN")
    if token:
        masked = token[:8] + "..." if len(token) > 8 else "***"
        print(f"  [OK] HF_TOKEN: set ({masked})")
        return True
    else:
        print("  [WARN] HF_TOKEN: not set")
        print("         PyAnnote Audio requires a HuggingFace token for gated models.")
        print("         1. Accept licences at: https://huggingface.co/pyannote/speaker-diarization-3.1")
        print("         2. Create a token at:  https://huggingface.co/settings/tokens")
        print("         3. Set it:")
        print("              Windows  : $env:HF_TOKEN = 'hf_...'")
        print("              macOS/Linux: export HF_TOKEN='hf_...'")
        return False
```

**Step 4: Update `main()` to call the new checks**

Find the existing section headers in `main()`. Change `[1/5]` through `[5/5]` to `[1/7]` through `[5/7]` and add two new sections before `[5/7] Backend API`.

Find this block in `main()`:

```python
    # Check backend API can be created
    print("[5/5] Backend API")
```

Replace with:

```python
    # Check system dependencies
    print("[6/7] System Dependencies")
    all_ok &= check_ffmpeg()
    print()

    # Check environment variables
    print("[7/7] Environment Variables")
    hf_ok = check_hf_token()
    if not hf_ok:
        print("         (Processing will still attempt to run; token needed for gated models only)")
    # HF_TOKEN missing is a warning, not a hard failure
    print()

    # Check backend API can be created
    print("[5/7] Backend API")
```

Also update the section numbering for the other sections (change `[2/5]` → `[2/7]`, `[3/5]` → `[3/7]`, `[4/5]` → `[4/7]`):

Find and replace each label:
- `"[2/5] Core ML Packages"` → `"[2/7] Core ML Packages"`
- `"[3/5] Video/Audio Processing"` → `"[3/7] Video/Audio Processing"`
- `"[4/5] FastAPI Backend"` → `"[4/7] FastAPI Backend"`

**Step 5: Run all tests**

```bash
python -m pytest tests/ -v
```

Expected: 21 passed (17 + 4 new).

**Step 6: Manually run the verify script to check output looks right**

```bash
python verify_environment.py
```

Expected: script runs to completion, shows `[6/7] System Dependencies` and `[7/7] Environment Variables` sections with appropriate PASS/FAIL/WARN for the current machine.

**Step 7: Lint**

```bash
black verify_environment.py
flake8 verify_environment.py --max-line-length=100 --extend-ignore=E203,W503,W293,E501
```

**Step 8: Commit**

```bash
git add verify_environment.py tests/test_verify_environment.py
git commit -m "feat: add FFmpeg and HF_TOKEN checks to verify_environment.py"
```

---

### Task 5: Final verification

**Step 1: Run full test suite**

```bash
python -m pytest tests/ -v --tb=short
```

Expected: 21 passed, 0 failed.

**Step 2: Run full lint**

```bash
black --check src/ verify_environment.py
flake8 src/ --max-line-length=100 --extend-ignore=E203,W503,W293,E501
```

Expected: no errors.

**Step 3: Run verify script**

```bash
python verify_environment.py
```

Confirm the two new sections appear correctly.

**Step 4: Final commit (if any uncommitted changes remain)**

```bash
git status
# If clean, no commit needed. If not:
git add -A
git commit -m "chore: production robustness pass complete"
```
