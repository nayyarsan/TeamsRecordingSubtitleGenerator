#!/usr/bin/env python3
"""
Verify the Webex Speaker Labeling environment setup.
Run this script to check if all dependencies are properly installed.
"""

import os
import shutil
import sys
from pathlib import Path


def check_module(name, package=None):
    """Check if a module can be imported."""
    import_name = package or name
    try:
        module = __import__(import_name)
        version = getattr(module, "__version__", "unknown")
        print(f"  [OK] {name}: {version}")
        return True
    except ImportError as e:
        print(f"  [FAIL] {name}: MISSING ({e})")
        return False


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
        print(
            "         1. Accept licences at: https://huggingface.co/pyannote/speaker-diarization-3.1"
        )
        print("         2. Create a token at:  https://huggingface.co/settings/tokens")
        print("         3. Set it:")
        print("              Windows  : $env:HF_TOKEN = 'hf_...'")
        print("              macOS/Linux: export HF_TOKEN='hf_...'")
        return False


def main():
    """Run environment verification checks."""
    print("=" * 60)
    print("Webex Speaker Labeling - Environment Verification")
    print("=" * 60)
    print()

    all_ok = True

    # Check Python version
    print("[1/7] Python Version")
    py_version = sys.version_info
    print(f"  [OK] Python {py_version.major}.{py_version.minor}.{py_version.micro}")
    if py_version < (3, 8):
        print("  [FAIL] ERROR: Python 3.8+ required")
        all_ok = False
    print()

    # Check core ML packages
    print("[2/7] Core ML Packages")
    all_ok &= check_module("PyTorch", "torch")
    all_ok &= check_module("PyAnnote.audio", "pyannote.audio")
    all_ok &= check_module("NumPy", "numpy")
    all_ok &= check_module("SciPy", "scipy")
    print()

    # Check video/audio processing
    print("[3/7] Video/Audio Processing")
    all_ok &= check_module("OpenCV", "cv2")
    all_ok &= check_module("MediaPipe", "mediapipe")
    all_ok &= check_module("Librosa", "librosa")
    all_ok &= check_module("Whisper", "whisper")
    print()

    # Check FastAPI backend
    print("[4/7] FastAPI Backend")
    all_ok &= check_module("FastAPI", "fastapi")
    all_ok &= check_module("Uvicorn", "uvicorn")
    all_ok &= check_module("SSE-Starlette", "sse_starlette")
    all_ok &= check_module("Python-multipart", "multipart")
    print()

    # Check backend API can be created
    print("[5/7] Backend API")
    try:
        from src.api import create_app

        app = create_app()
        print(f"  [OK] API app created: {app.title} v{app.version}")
    except Exception as e:
        print(f"  [FAIL] Failed to create API app: {e}")
        all_ok = False
    print()

    # Check system dependencies
    print("[6/7] System Dependencies")
    all_ok &= check_ffmpeg()
    print()

    # Check environment variables
    print("[7/7] Environment Variables")
    hf_ok = check_hf_token()
    if not hf_ok:
        print(
            "         (Processing will still attempt to run; token needed for gated models only)"
        )
    # HF_TOKEN missing is a warning, not a hard failure
    print()

    # Check project directories
    print("Project Directories:")
    dirs = ["src", "frontend", "output", "uploads"]
    for d in dirs:
        path = Path(d)
        status = "[OK]" if path.exists() else "[MISSING]"
        print(f"  {status} {d}/")
    print()

    # Final summary
    print("=" * 60)
    if all_ok:
        print("[SUCCESS] ALL CHECKS PASSED - Environment ready!")
        print()
        print("Next steps:")
        print("  1. Start backend: python run_server.py")
        print("  2. Start frontend: cd frontend && npm run dev")
        print("  3. Open browser: http://localhost:3000")
        return 0
    else:
        print("[FAIL] SOME CHECKS FAILED - Please install missing dependencies")
        print()
        print("To install:")
        print('  pip install -e ".[dev,llm]"')
        return 1


if __name__ == "__main__":
    sys.exit(main())
