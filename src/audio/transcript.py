"""Transcript parsing and processing module."""

import re
from pathlib import Path
from typing import List, Dict, Optional
from dataclasses import dataclass
import pysrt
import webvtt
import json

from ..utils import get_logger


logger = get_logger(__name__)


@dataclass
class TranscriptSegment:
    """Represents a segment from the transcript."""
    start: float
    end: float
    text: str
    speaker: Optional[str] = None  # Original speaker label from Webex
    
    @property
    def duration(self) -> float:
        """Get segment duration."""
        return self.end - self.start


class TranscriptParser:
    """Handles parsing of various transcript formats."""

    @staticmethod
    def transcribe_audio(
        audio_path: Path,
        model_size: str = "base",
        language: Optional[str] = None
    ) -> List[TranscriptSegment]:
        """
        Transcribe audio into transcript segments using Whisper.

        Args:
            audio_path: Path to audio file
            model_size: Whisper model size (tiny, base, small, medium, large)
            language: Optional language code (e.g., en, fr, es)

        Returns:
            List of transcript segments
        """
        logger.info(f"Transcribing audio with Whisper model '{model_size}'")

        try:
            import whisper
            import librosa
            import numpy as np
        except Exception as e:
            raise ValueError(
                "Whisper is not installed. Install 'openai-whisper' to use auto-transcription."
            ) from e

        try:
            # Pre-load audio with librosa to avoid ffmpeg dependency
            logger.info("Loading audio file...")
            audio, sr = librosa.load(str(audio_path), sr=16000, mono=True)
            
            model = whisper.load_model(model_size)
            logger.info("Running speech recognition...")
            result = model.transcribe(
                audio,
                language=language,
                task="transcribe"
            )
        except Exception as e:
            raise ValueError(f"Audio transcription failed: {e}") from e

        segments = []
        for seg in result.get("segments", []):
            segments.append(TranscriptSegment(
                start=float(seg.get("start", 0.0)),
                end=float(seg.get("end", 0.0)),
                text=(seg.get("text", "") or "").strip(),
                speaker=None
            ))

        logger.info(f"Transcription complete: {len(segments)} segments")
        return segments
    
    @staticmethod
    def parse_srt(file_path: Path) -> List[TranscriptSegment]:
        """
        Parse SRT subtitle file.
        
        Args:
            file_path: Path to SRT file
        
        Returns:
            List of transcript segments
        """
        logger.info(f"Parsing SRT file: {file_path}")
        
        try:
            subs = pysrt.open(str(file_path))
            segments = []
            
            for sub in subs:
                # Convert timestamp to seconds
                start = (
                    sub.start.hours * 3600 +
                    sub.start.minutes * 60 +
                    sub.start.seconds +
                    sub.start.milliseconds / 1000
                )
                end = (
                    sub.end.hours * 3600 +
                    sub.end.minutes * 60 +
                    sub.end.seconds +
                    sub.end.milliseconds / 1000
                )
                
                # Extract speaker label if present (format: "Speaker: text")
                text = sub.text.replace('\n', ' ')
                speaker = None
                
                speaker_match = re.match(r'^([^:]+):\s*(.*)$', text)
                if speaker_match:
                    speaker = speaker_match.group(1).strip()
                    text = speaker_match.group(2).strip()
                
                segments.append(TranscriptSegment(
                    start=start,
                    end=end,
                    text=text,
                    speaker=speaker
                ))
            
            logger.info(f"Parsed {len(segments)} segments from SRT")
            return segments
            
        except Exception as e:
            logger.error(f"Failed to parse SRT file: {e}")
            raise
    
    @staticmethod
    def parse_vtt(file_path: Path) -> List[TranscriptSegment]:
        """
        Parse WebVTT subtitle file.
        
        Args:
            file_path: Path to VTT file
        
        Returns:
            List of transcript segments
        """
        logger.info(f"Parsing VTT file: {file_path}")
        
        try:
            segments = []
            
            for caption in webvtt.read(str(file_path)):
                # Parse timestamp (format: HH:MM:SS.mmm)
                start = TranscriptParser._parse_vtt_timestamp(caption.start)
                end = TranscriptParser._parse_vtt_timestamp(caption.end)
                
                # Extract speaker and text
                text = caption.text.replace('\n', ' ')
                speaker = None
                
                speaker_match = re.match(r'^([^:]+):\s*(.*)$', text)
                if speaker_match:
                    speaker = speaker_match.group(1).strip()
                    text = speaker_match.group(2).strip()
                
                segments.append(TranscriptSegment(
                    start=start,
                    end=end,
                    text=text,
                    speaker=speaker
                ))
            
            logger.info(f"Parsed {len(segments)} segments from VTT")
            return segments
            
        except Exception as e:
            logger.error(f"Failed to parse VTT file: {e}")
            raise
    
    @staticmethod
    def parse_json(file_path: Path) -> List[TranscriptSegment]:
        """
        Parse JSON transcript file (Webex format).
        
        Expected format:
        {
            "segments": [
                {
                    "start": 0.0,
                    "end": 5.0,
                    "text": "Hello everyone",
                    "speaker": "Speaker 1"
                }
            ]
        }
        
        Args:
            file_path: Path to JSON file
        
        Returns:
            List of transcript segments
        """
        logger.info(f"Parsing JSON file: {file_path}")
        
        try:
            with open(file_path, 'r') as f:
                data = json.load(f)
            
            segments = []
            
            # Handle different JSON structures
            if 'segments' in data:
                items = data['segments']
            elif isinstance(data, list):
                items = data
            else:
                raise ValueError("Unsupported JSON structure")
            
            for item in items:
                segments.append(TranscriptSegment(
                    start=float(item.get('start', 0)),
                    end=float(item.get('end', 0)),
                    text=item.get('text', ''),
                    speaker=item.get('speaker')
                ))
            
            logger.info(f"Parsed {len(segments)} segments from JSON")
            return segments
            
        except Exception as e:
            logger.error(f"Failed to parse JSON file: {e}")
            raise
    
    @staticmethod
    def _parse_vtt_timestamp(timestamp: str) -> float:
        """
        Convert VTT timestamp to seconds.
        
        Args:
            timestamp: Timestamp string (HH:MM:SS.mmm or MM:SS.mmm)
        
        Returns:
            Time in seconds
        """
        parts = timestamp.split(':')
        
        if len(parts) == 3:
            # HH:MM:SS.mmm
            hours, minutes, seconds = parts
            return (
                int(hours) * 3600 +
                int(minutes) * 60 +
                float(seconds)
            )
        elif len(parts) == 2:
            # MM:SS.mmm
            minutes, seconds = parts
            return int(minutes) * 60 + float(seconds)
        else:
            raise ValueError(f"Invalid timestamp format: {timestamp}")
    
    @staticmethod
    def parse(file_path: Path) -> List[TranscriptSegment]:
        """
        Auto-detect format and parse transcript file.
        
        Args:
            file_path: Path to transcript file
        
        Returns:
            List of transcript segments
        """
        suffix = file_path.suffix.lower()
        
        if suffix == '.srt':
            return TranscriptParser.parse_srt(file_path)
        elif suffix == '.vtt':
            return TranscriptParser.parse_vtt(file_path)
        elif suffix == '.json':
            return TranscriptParser.parse_json(file_path)
        else:
            raise ValueError(f"Unsupported transcript format: {suffix}")
