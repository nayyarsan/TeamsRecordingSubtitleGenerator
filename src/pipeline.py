"""Main processing pipeline orchestrator."""

from pathlib import Path
from typing import Optional, Dict
import tempfile
import shutil
from tqdm import tqdm

from .audio import AudioProcessor, TranscriptParser
from .video import VideoProcessor
from .fusion import AudioVisualFusion
from .naming import SpeakerNamer
from .output import OutputGenerator
from .utils import get_logger, get_config, setup_logger


logger = get_logger(__name__)


class MeetingProcessor:
    """Main pipeline for processing Webex meeting recordings."""
    
    def __init__(self, config_path: Optional[Path] = None, verbose: bool = False):
        """
        Initialize meeting processor.
        
        Args:
            config_path: Path to configuration file
            verbose: Enable verbose logging
        """
        # Setup logging
        setup_logger('webex-speaker-labeling', verbose=verbose)
        
        # Load configuration
        if config_path:
            from .utils.config import reload_config
            reload_config(str(config_path))
        
        self.config = get_config()
        
        # Initialize components
        self.audio_processor = AudioProcessor()
        self.video_processor = VideoProcessor()
        self.fusion_processor = AudioVisualFusion()
        self.speaker_namer = SpeakerNamer()
        self.output_generator = OutputGenerator()
        
        # Processing config
        processing_config = self.config.get_processing_config()
        self.temp_dir = Path(processing_config.get('temp_dir', './temp'))
        self.cleanup_temp = processing_config.get('cleanup_temp', True)
        
        logger.info("MeetingProcessor initialized")
    
    def process(
        self,
        video_path: Path,
        transcript_path: Path,
        output_dir: Path
    ) -> Dict[str, Path]:
        """
        Process a meeting recording end-to-end.
        
        Args:
            video_path: Path to meeting video file
            transcript_path: Path to transcript file
            output_dir: Directory for output files
        
        Returns:
            Dictionary of output file paths
        """
        logger.info("=" * 80)
        logger.info("Starting meeting processing pipeline")
        logger.info(f"Video: {video_path}")
        logger.info(f"Transcript: {transcript_path}")
        logger.info(f"Output: {output_dir}")
        logger.info("=" * 80)
        
        # Validate inputs
        self._validate_inputs(video_path, transcript_path)
        
        # Create directories
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        
        try:
            # Step 1: Extract audio and perform diarization
            logger.info("\n[1/5] Extracting audio and performing diarization...")
            audio_path = self.audio_processor.extract_audio(
                video_path,
                self.temp_dir / f"{video_path.stem}_audio.wav"
            )
            
            diarization_segments = self.audio_processor.perform_diarization(audio_path)
            
            audio_stats = self.audio_processor.get_speaker_statistics(diarization_segments)
            logger.info(f"Audio diarization complete: {len(audio_stats)} speakers detected")
            for speaker_id, stats in audio_stats.items():
                logger.info(f"  {speaker_id}: {stats['total_duration']:.1f}s "
                          f"({stats['segment_count']} segments)")
            
            # Step 2: Parse transcript
            logger.info("\n[2/5] Parsing transcript...")
            transcript_segments = TranscriptParser.parse(transcript_path)
            logger.info(f"Transcript parsed: {len(transcript_segments)} segments")
            
            # Step 3: Process video and detect faces
            logger.info("\n[3/5] Processing video and detecting faces...")
            frame_data_list = self.video_processor.process_video(video_path)
            
            video_stats = self.video_processor.get_face_statistics()
            logger.info(f"Video processing complete: {len(video_stats)} faces tracked")
            for face_id, stats in video_stats.items():
                logger.info(f"  {face_id}: {stats['duration']:.1f}s "
                          f"({stats['frame_count']} frames)")
            
            # Step 4: Fuse audio and video
            logger.info("\n[4/5] Fusing audio and video data...")
            fused_segments = self.fusion_processor.fuse(
                diarization_segments,
                frame_data_list
            )
            
            fusion_stats = self.fusion_processor.get_statistics(fused_segments)
            logger.info(f"Fusion complete: {fusion_stats['segments_with_faces']}/{fusion_stats['total_segments']} "
                       f"segments with faces")
            
            # Build speaker-face mapping
            speaker_face_mapping = self.fusion_processor.build_speaker_face_mapping(
                fused_segments
            )
            
            # Step 5: Extract speaker names
            logger.info("\n[5/5] Extracting speaker names...")
            named_speakers = self.speaker_namer.extract_names(
                transcript_segments,
                fused_segments
            )
            
            speaker_mapping = self.speaker_namer.create_speaker_mapping(named_speakers)
            logger.info(f"Speaker naming complete: {len(speaker_mapping)} speakers named")
            for speaker_id, name in speaker_mapping.items():
                logger.info(f"  {speaker_id} -> {name}")
            
            # Step 6: Generate outputs
            logger.info("\nGenerating output files...")
            
            output_files = {}
            
            # Generate SRT
            srt_path = output_dir / f"{video_path.stem}_labeled.srt"
            self.output_generator.generate_srt(
                transcript_segments,
                fused_segments,
                speaker_mapping,
                srt_path
            )
            output_files['srt'] = srt_path
            
            # Generate JSON
            json_path = output_dir / f"{video_path.stem}_labeled.json"
            self.output_generator.generate_json(
                transcript_segments,
                fused_segments,
                speaker_mapping,
                named_speakers,
                json_path
            )
            output_files['json'] = json_path
            
            logger.info("\n" + "=" * 80)
            logger.info("Processing complete!")
            logger.info(f"SRT output: {srt_path}")
            logger.info(f"JSON output: {json_path}")
            logger.info("=" * 80)
            
            return output_files
            
        except Exception as e:
            logger.error(f"Processing failed: {e}", exc_info=True)
            raise
            
        finally:
            # Cleanup temporary files
            if self.cleanup_temp and self.temp_dir.exists():
                logger.info("Cleaning up temporary files...")
                shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def _validate_inputs(self, video_path: Path, transcript_path: Path):
        """
        Validate input files.
        
        Args:
            video_path: Path to video file
            transcript_path: Path to transcript file
        
        Raises:
            FileNotFoundError: If files don't exist
            ValueError: If file formats are unsupported
        """
        # Check video file
        if not video_path.exists():
            raise FileNotFoundError(f"Video file not found: {video_path}")
        
        if video_path.suffix.lower() not in ['.mp4', '.avi', '.mov', '.mkv']:
            logger.warning(f"Unsupported video format: {video_path.suffix}. "
                          f"Attempting to process anyway...")
        
        # Check transcript file
        if not transcript_path.exists():
            raise FileNotFoundError(f"Transcript file not found: {transcript_path}")
        
        if transcript_path.suffix.lower() not in ['.srt', '.vtt', '.json']:
            raise ValueError(f"Unsupported transcript format: {transcript_path.suffix}. "
                           f"Supported formats: .srt, .vtt, .json")
        
        logger.info("Input validation passed")


def process_meeting(
    video_path: str,
    transcript_path: str,
    output_dir: str,
    config_path: Optional[str] = None,
    verbose: bool = False
) -> Dict[str, Path]:
    """
    Convenience function to process a meeting.
    
    Args:
        video_path: Path to video file
        transcript_path: Path to transcript file
        output_dir: Output directory
        config_path: Optional config file path
        verbose: Enable verbose logging
    
    Returns:
        Dictionary of output file paths
    """
    processor = MeetingProcessor(
        config_path=Path(config_path) if config_path else None,
        verbose=verbose
    )
    
    return processor.process(
        Path(video_path),
        Path(transcript_path),
        Path(output_dir)
    )
