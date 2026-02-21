"""Main processing pipeline orchestrator."""

from pathlib import Path
from typing import Optional, Dict, Callable, List
import shutil
import threading

from .audio import AudioProcessor, TranscriptParser
from .video import VideoProcessor
from .fusion import AudioVisualFusion
from .naming import SpeakerNamer
from .output import OutputGenerator
from .visualizer import VideoVisualizer
from .utils import get_logger, get_config, setup_logger

logger = get_logger(__name__)


class MeetingProcessor:
    """Main pipeline for processing Webex meeting recordings."""

    def __init__(
        self,
        config_path: Optional[Path] = None,
        verbose: bool = False,
        progress_callback: Optional[Callable[[str, int, str], None]] = None,
    ):
        """
        Initialize meeting processor.

        Args:
            config_path: Path to configuration file
            verbose: Enable verbose logging
            progress_callback: Optional callback(step_name, percent, message)
        """
        # Setup logging
        setup_logger("webex-speaker-labeling", verbose=verbose)

        # Load configuration
        if config_path:
            from .utils.config import reload_config

            reload_config(str(config_path))

        self.config = get_config()

        # Progress tracking (thread-safe)
        self._lock = threading.Lock()
        self._progress_callback = progress_callback
        self.current_step: str = "idle"
        self.current_percent: int = 0
        self.log_buffer: List[Dict] = []

        # Initialize components (audio_processor will be set per-process)
        self.audio_processor = None
        self.video_processor = VideoProcessor()
        self.fusion_processor = AudioVisualFusion()
        self.speaker_namer = SpeakerNamer()
        self.output_generator = OutputGenerator()
        self.video_visualizer = VideoVisualizer()

        # Processing config
        processing_config = self.config.get_processing_config()
        self.temp_dir = Path(processing_config.get("temp_dir", "./temp"))
        self.cleanup_temp = processing_config.get("cleanup_temp", True)

        logger.info("MeetingProcessor initialized")

    def _update_progress(
        self, step: str, percent: int, message: str, level: str = "info"
    ):
        """Update progress state and invoke callback (thread-safe)."""
        with self._lock:
            self.current_step = step
            self.current_percent = percent
            self.log_buffer.append(
                {"step": step, "percent": percent, "message": message, "level": level}
            )
        if self._progress_callback:
            self._progress_callback(step, percent, message, level)

    def _warn(self, message: str) -> None:
        """Send a warning-level message through the progress callback."""
        self._update_progress(
            self.current_step, self.current_percent, message, level="warning"
        )

    def _count_total_faces(self, frame_data_list: list) -> int:
        """Count total face detections across all frames."""
        return sum(len(frame_faces) for frame_faces in frame_data_list)

    def get_progress(self) -> Dict:
        """Get current progress state (thread-safe)."""
        with self._lock:
            return {
                "step": self.current_step,
                "percent": self.current_percent,
                "logs": list(self.log_buffer),
            }

    def process(
        self,
        video_path: Path,
        transcript_path: Optional[Path],
        output_dir: Path,
        asr_model: Optional[str] = None,
        asr_language: Optional[str] = None,
        ffmpeg_path: Optional[str] = None,
        generate_annotated_video: bool = False,
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
        if transcript_path:
            logger.info(f"Transcript: {transcript_path}")
        else:
            logger.info("Transcript: <auto-transcribe>")
        logger.info(f"Output: {output_dir}")
        logger.info("=" * 80)

        # Validate inputs
        self._validate_inputs(video_path, transcript_path)

        # Create directories
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        self.temp_dir.mkdir(parents=True, exist_ok=True)

        # Initialize AudioProcessor with ffmpeg_path (each process call may have different path)
        self.audio_processor = AudioProcessor(ffmpeg_path=ffmpeg_path)

        try:
            # Step 1: Extract audio and perform diarization
            self._update_progress(
                "diarization", 0, "Extracting audio and performing diarization..."
            )
            logger.info("\n[1/6] Extracting audio and performing diarization...")
            audio_path = self.audio_processor.extract_audio(
                video_path, self.temp_dir / f"{video_path.stem}_audio.wav"
            )

            diarization_segments = self.audio_processor.perform_diarization(audio_path)

            audio_stats = self.audio_processor.get_speaker_statistics(
                diarization_segments
            )
            logger.info(
                f"Audio diarization complete: {len(audio_stats)} speakers detected"
            )
            for speaker_id, stats in audio_stats.items():
                logger.info(
                    f"  {speaker_id}: {stats['total_duration']:.1f}s "
                    f"({stats['segment_count']} segments)"
                )

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

            # Step 3: Process video and detect faces
            self._update_progress(
                "face_detection", 35, "Processing video and detecting faces..."
            )
            logger.info("\n[3/6] Processing video and detecting faces...")
            frame_data_list = self.video_processor.process_video(video_path)

            video_stats = self.video_processor.get_face_statistics()
            logger.info(f"Video processing complete: {len(video_stats)} faces tracked")
            for face_id, stats in video_stats.items():
                logger.info(
                    f"  {face_id}: {stats['duration']:.1f}s "
                    f"({stats['frame_count']} frames)"
                )

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

            # Build speaker-face mapping (retained for future use)
            _speaker_face_mapping = self.fusion_processor.build_speaker_face_mapping(  # noqa: F841
                fused_segments
            )

            # Step 5: Extract speaker names
            self._update_progress("naming", 70, "Extracting speaker names...")
            logger.info("\n[5/6] Extracting speaker names...")
            named_speakers = self.speaker_namer.extract_names(
                transcript_segments, fused_segments
            )

            speaker_mapping = self.speaker_namer.create_speaker_mapping(named_speakers)
            logger.info(
                f"Speaker naming complete: {len(speaker_mapping)} speakers named"
            )
            for speaker_id, name in speaker_mapping.items():
                logger.info(f"  {speaker_id} -> {name}")

            # Step 6: Generate outputs
            self._update_progress("output", 85, "Generating output files...")
            logger.info("\n[6/6] Generating output files...")

            output_files = {}

            # Generate SRT
            srt_path = output_dir / f"{video_path.stem}_labeled.srt"
            self.output_generator.generate_srt(
                transcript_segments, fused_segments, speaker_mapping, srt_path
            )
            output_files["srt"] = srt_path

            # Generate JSON
            json_path = output_dir / f"{video_path.stem}_labeled.json"
            self.output_generator.generate_json(
                transcript_segments,
                fused_segments,
                speaker_mapping,
                named_speakers,
                json_path,
            )
            output_files["json"] = json_path

            # Generate face data JSON
            faces_path = output_dir / f"{video_path.stem}_faces.json"
            self.output_generator.generate_face_data(
                frame_data_list, speaker_mapping, faces_path
            )
            output_files["faces"] = faces_path

            # Generate annotated video (optional)
            if generate_annotated_video:
                logger.info("\nGenerating annotated video with face detection...")
                annotated_video_path = output_dir / f"{video_path.stem}_annotated.mp4"
                try:
                    self.video_visualizer.create_annotated_video(
                        video_path,
                        frame_data_list,
                        fused_segments,
                        speaker_mapping,
                        transcript_segments,
                        annotated_video_path,
                        ffmpeg_path,
                    )
                    output_files["annotated_video"] = annotated_video_path
                except Exception as e:
                    logger.warning(f"Could not generate annotated video: {e}")

            self._update_progress("complete", 100, "Processing complete!")
            logger.info("\n" + "=" * 80)
            logger.info("Processing complete!")
            logger.info(f"SRT output: {srt_path}")
            logger.info(f"JSON output: {json_path}")
            if "annotated_video" in output_files:
                logger.info(f"Annotated video: {annotated_video_path}")
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

    def _validate_inputs(self, video_path: Path, transcript_path: Optional[Path]):
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

        if video_path.suffix.lower() not in [".mp4", ".avi", ".mov", ".mkv"]:
            logger.warning(
                f"Unsupported video format: {video_path.suffix}. "
                f"Attempting to process anyway..."
            )

        # Check transcript file (optional)
        if transcript_path:
            if not transcript_path.exists():
                raise FileNotFoundError(f"Transcript file not found: {transcript_path}")

            if transcript_path.suffix.lower() not in [".srt", ".vtt", ".json"]:
                raise ValueError(
                    f"Unsupported transcript format: {transcript_path.suffix}. "
                    f"Supported formats: .srt, .vtt, .json"
                )

        logger.info("Input validation passed")


def process_meeting(
    video_path: str,
    transcript_path: str,
    output_dir: str,
    config_path: Optional[str] = None,
    verbose: bool = False,
    ffmpeg_path: Optional[str] = None,
    asr_model: Optional[str] = None,
    asr_language: Optional[str] = None,
    generate_annotated_video: bool = False,
) -> Dict[str, Path]:
    """
    Convenience function to process a meeting.

    Args:
        video_path: Path to video file
        transcript_path: Path to transcript file
        output_dir: Output directory
        config_path: Optional config file path
        verbose: Enable verbose logging
        ffmpeg_path: Optional ffmpeg executable path
        asr_model: Optional Whisper ASR model
        asr_language: Optional language for ASR
        generate_annotated_video: Generate annotated video with face detection

    Returns:
        Dictionary of output file paths
    """
    processor = MeetingProcessor(
        config_path=Path(config_path) if config_path else None, verbose=verbose
    )

    return processor.process(
        Path(video_path),
        Path(transcript_path) if transcript_path else None,
        Path(output_dir),
        asr_model=asr_model,
        asr_language=asr_language,
        ffmpeg_path=ffmpeg_path,
        generate_annotated_video=generate_annotated_video,
    )
