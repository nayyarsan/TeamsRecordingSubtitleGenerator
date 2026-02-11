"""
Webex Meeting Speaker Labeling Tool

An offline Python tool for post-processing Webex meeting recordings
to identify and label speakers using audio diarization and video analysis.
"""

__version__ = "0.1.0"
__author__ = "Your Team"

from .pipeline import MeetingProcessor

__all__ = ["MeetingProcessor"]
