"""Tests for pipeline robustness additions."""

from unittest.mock import MagicMock, patch


def _make_processor(callback=None):
    """Create a MeetingProcessor with all heavy sub-components mocked out."""
    with (
        patch("src.pipeline.VideoProcessor"),
        patch("src.pipeline.AudioVisualFusion"),
        patch("src.pipeline.SpeakerNamer"),
        patch("src.pipeline.OutputGenerator"),
        patch("src.pipeline.VideoVisualizer"),
        patch("src.pipeline.setup_logger"),
    ):
        from src.pipeline import MeetingProcessor

        return MeetingProcessor(progress_callback=callback)


def test_warn_logs_entry_at_warning_level():
    proc = _make_processor()
    proc.current_step = "testing"
    proc.current_percent = 42
    proc._warn("something went wrong")

    warning_entries = [
        log for log in proc.log_buffer if log.get("level") == "warning"
    ]
    assert len(warning_entries) == 1
    assert "something went wrong" in warning_entries[0]["message"]


def test_update_progress_passes_level_to_callback():
    received = []

    def cb(step, pct, msg, level="info"):
        received.append(level)

    proc = _make_processor(callback=cb)
    proc._update_progress("step", 10, "msg", level="warning")
    assert received == ["warning"]


def test_count_total_faces_returns_zero_for_empty_list():
    proc = _make_processor()
    assert proc._count_total_faces([]) == 0


def test_count_total_faces_sums_across_frames():
    proc = _make_processor()
    # frame_data_list: list of frames, each frame is a list of face detections
    frame_data = [["face1", "face2"], [], ["face3"]]
    assert proc._count_total_faces(frame_data) == 3
