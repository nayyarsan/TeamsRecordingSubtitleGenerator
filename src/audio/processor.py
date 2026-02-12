"""Audio processing and diarization module."""

import numpy as np
import torch
import torchaudio
from pathlib import Path
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
import subprocess
import tempfile
import shutil

from pyannote.audio import Pipeline
from pyannote.core import Segment, Annotation

from ..utils import get_logger, get_config


logger = get_logger(__name__)


@dataclass
class DiarizationSegment:
    """Represents a speaker segment from diarization."""
    speaker_id: str
    start: float
    end: float
    confidence: float = 1.0
    
    @property
    def duration(self) -> float:
        """Get segment duration."""
        return self.end - self.start


class AudioProcessor:
    """Handles audio extraction and diarization."""
    
    def __init__(self, config: Optional[Dict] = None, ffmpeg_path: Optional[str] = None):
        """
        Initialize audio processor.
        
        Args:
            config: Audio configuration dictionary
            ffmpeg_path: Optional path to ffmpeg executable
        """
        if config is None:
            config = get_config().get_audio_config()
        
        self.config = config
        self.sample_rate = config.get('sample_rate', 16000)
        self.audio_format = config.get('format', 'wav')
        self.ffmpeg_path = ffmpeg_path
        
        # Diarization settings
        diar_config = config.get('diarization', {})
        self.max_speakers = diar_config.get('max_speakers', 10)
        self.min_segment_duration = diar_config.get('min_segment_duration', 0.5)
        
        # Pipeline will be loaded lazily
        self._diarization_pipeline = None
        
        logger.info("AudioProcessor initialized")
    
    def extract_audio(
        self, 
        video_path: Path, 
        output_path: Optional[Path] = None
    ) -> Path:
        """
        Extract audio track from video file.
        
        Args:
            video_path: Path to input video file
            output_path: Path for output audio file
        
        Returns:
            Path to extracted audio file
        """
        logger.info(f"Extracting audio from {video_path}")
        
        if output_path is None:
            output_path = video_path.parent / f"{video_path.stem}_audio.{self.audio_format}"
        
        # Use ffmpeg for audio extraction
        ffmpeg_bin = self.ffmpeg_path or shutil.which('ffmpeg')
        if not ffmpeg_bin:
            raise FileNotFoundError(
                "ffmpeg not found on PATH. Install ffmpeg (full-shared build on Windows) "
                "and ensure it is available in your PATH, or use --ffmpeg-path to specify the path."
            )

        cmd = [
            ffmpeg_bin,
            '-i', str(video_path),
            '-vn',  # No video
            '-acodec', 'pcm_s16le',  # PCM audio codec
            '-ar', str(self.sample_rate),  # Sample rate
            '-ac', '1',  # Mono channel
            '-y',  # Overwrite output
            str(output_path)
        ]
        
        try:
            subprocess.run(
                cmd,
                check=True,
                capture_output=True,
                text=True
            )
            logger.info(f"Audio extracted to {output_path}")
            return output_path
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to extract audio: {e.stderr}")
            raise RuntimeError(f"Audio extraction failed: {e.stderr}")
    
    def load_diarization_pipeline(self):
        """Load pyannote diarization pipeline."""
        if self._diarization_pipeline is None:
            logger.info("Loading diarization pipeline...")
            try:
                import os
                # Get token from environment
                token = os.environ.get('HF_TOKEN')
                
                if not token:
                    logger.warning("HF_TOKEN not set. Attempting to load without token (may fail for gated models).")
                
                # Use CPU-friendly pipeline for Pyannote 3.1+
                # Build kwargs with only valid parameters
                kwargs = {}
                if token:
                    kwargs["token"] = token
                
                logger.info("Loading speaker-diarization-3.1 model...")
                self._diarization_pipeline = Pipeline.from_pretrained(
                    "pyannote/speaker-diarization-3.1",
                    **kwargs
                )
                
                # Force CPU usage (move pipeline to CPU after loading)
                if torch.cuda.is_available():
                    logger.warning("GPU detected but using CPU for MVP")
                    self._diarization_pipeline.to(torch.device("cpu"))
                
                logger.info("Diarization pipeline loaded successfully")
            except Exception as e:
                logger.error(f"Failed to load diarization pipeline: {e}")
                logger.info("\nTo use the speaker diarization feature:")
                logger.info("1. Visit and accept: https://huggingface.co/pyannote/speaker-diarization-3.1")
                logger.info("2. Visit and accept: https://huggingface.co/pyannote/segmentation-3.0")
                logger.info("3. Create token: https://huggingface.co/settings/tokens")
                logger.info("4. Set token: $env:HF_TOKEN = 'hf_your_token_here'")
                logger.info("5. Run pipeline again")
                raise
    
    def perform_diarization(
        self, 
        audio_path: Path
    ) -> List[DiarizationSegment]:
        """
        Perform speaker diarization on audio file.
        
        Args:
            audio_path: Path to audio file
        
        Returns:
            List of diarization segments
        """
        logger.info(f"Starting diarization on {audio_path}")
        
        # Load pipeline if not already loaded
        self.load_diarization_pipeline()
        
        # Run diarization
        try:
            # Pre-load audio using librosa to avoid torchcodec issues
            logger.info("Loading audio file with librosa...")
            import librosa
            
            # Load audio with librosa (no torchcodec dependency)
            waveform_np, sr = librosa.load(str(audio_path), sr=None, mono=True)
            
            # Resample to 16kHz if needed
            if sr != 16000:
                logger.info(f"Resampling from {sr}Hz to 16kHz")
                waveform_np = librosa.resample(waveform_np, orig_sr=sr, target_sr=16000)
                sr = 16000
            
            # Convert to torch tensor (N, T) format
            waveform = torch.from_numpy(waveform_np).float().unsqueeze(0)
            
            # Create file dict in format Pyannote expects
            file = {
                "waveform": waveform,
                "sample_rate": 16000
            }
            
            logger.info(f"Running diarization (audio duration: {waveform.shape[1] / 16000:.1f}s)")
            output = self._diarization_pipeline(file)
            
            # Handle different output formats from Pyannote 3.1+
            # DiarizeOutput has different structure than Annotation
            logger.info(f"Diarization output type: {type(output)}")
            
            # Convert diarization output to our segment format
            segments = []
            
            # Try different methods to access the diarization data
            if hasattr(output, '__iter__'):
                # If it's iterable, iterate directly
                for turn, _, speaker in output:
                    segment = DiarizationSegment(
                        speaker_id=speaker,
                        start=turn.start,
                        end=turn.end,
                        confidence=1.0
                    )
                    segments.append(segment)
            elif hasattr(output, 'itertracks'):
                # If it has itertracks method (Annotation)
                for turn, _, speaker in output.itertracks(yield_label=True):
                    segment = DiarizationSegment(
                        speaker_id=speaker,
                        start=turn.start,
                        end=turn.end,
                        confidence=1.0
                    )
                    segments.append(segment)
            elif hasattr(output, 'segments'):
                # If it has segments attribute
                for seg in output.segments:
                    segment = DiarizationSegment(
                        speaker_id=seg.label,
                        start=seg.start,
                        end=seg.end,
                        confidence=1.0
                    )
                    segments.append(segment)
            else:
                # Try to get the annotation directly
                diarization = output
                if hasattr(diarization, 'itertracks'):
                    for turn, _, speaker in diarization.itertracks(yield_label=True):
                        segment = DiarizationSegment(
                            speaker_id=speaker,
                            start=turn.start,
                            end=turn.end,
                            confidence=1.0
                        )
                        segments.append(segment)
            
            logger.info(f"Diarization complete: {len(segments)} segments from {len(set([s.speaker_id for s in segments]))} speakers")
            return segments
        except Exception as e:
            logger.error(f"Diarization failed: {e}")
            raise RuntimeError(f"Diarization failed: {e}")
    
    def get_speaker_statistics(
        self, 
        segments: List[DiarizationSegment]
    ) -> Dict[str, Dict]:
        """
        Calculate speaking statistics for each speaker.
        
        Args:
            segments: List of diarization segments
        
        Returns:
            Dictionary mapping speaker_id to statistics
        """
        stats = {}
        
        for segment in segments:
            if segment.speaker_id not in stats:
                stats[segment.speaker_id] = {
                    'total_duration': 0.0,
                    'segment_count': 0,
                    'avg_segment_duration': 0.0
                }
            
            stats[segment.speaker_id]['total_duration'] += segment.duration
            stats[segment.speaker_id]['segment_count'] += 1
        
        # Calculate averages
        for speaker_id, speaker_stats in stats.items():
            speaker_stats['avg_segment_duration'] = (
                speaker_stats['total_duration'] / speaker_stats['segment_count']
            )
        
        return stats


def extract_and_diarize(
    video_path: Path,
    output_dir: Optional[Path] = None
) -> Tuple[Path, List[DiarizationSegment]]:
    """
    Convenience function to extract audio and perform diarization.
    
    Args:
        video_path: Path to video file
        output_dir: Directory for output files
    
    Returns:
        Tuple of (audio_path, diarization_segments)
    """
    processor = AudioProcessor()
    
    # Extract audio
    if output_dir:
        audio_path = output_dir / f"{video_path.stem}_audio.wav"
    else:
        audio_path = None
    
    audio_path = processor.extract_audio(video_path, audio_path)
    
    # Perform diarization
    segments = processor.perform_diarization(audio_path)
    
    return audio_path, segments
