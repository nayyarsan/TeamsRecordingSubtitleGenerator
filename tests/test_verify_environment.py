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
