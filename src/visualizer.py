"""Video visualization module for face detection and subtitle overlay."""

import cv2
import numpy as np
from pathlib import Path
from typing import List, Dict, Tuple, Optional
from datetime import timedelta
import subprocess

from .video.processor import FrameData, Face
from .audio.transcript import TranscriptSegment
from .fusion.processor import SpeakerSegment
from .utils import get_logger, get_config


logger = get_logger(__name__)


class VideoVisualizer:
    """Handles creation of annotated videos with face detection and subtitles."""
    
    def __init__(self, config: Optional[Dict] = None):
        """
        Initialize video visualizer.
        
        Args:
            config: Visualization configuration dictionary
        """
        if config is None:
            config = get_config().get('visualization', {})
        
        self.config = config
        self.font = cv2.FONT_HERSHEY_SIMPLEX
        self.font_scale = 0.6
        self.font_color = (0, 255, 0)  # Green
        self.font_thickness = 2
        
        # Face box colors by confidence
        self.high_confidence_color = (0, 255, 0)  # Green
        self.medium_confidence_color = (0, 165, 255)  # Orange
        self.low_confidence_color = (0, 0, 255)  # Red
        
        # Subtitle settings
        self.subtitle_height = 100
        self.subtitle_bg_color = (0, 0, 0)
        self.subtitle_text_color = (255, 255, 255)  # White
        self.subtitle_font_scale = 0.8
        
        logger.info("VideoVisualizer initialized")
    
    def create_annotated_video(
        self,
        video_path: Path,
        frame_data_list: List[FrameData],
        fused_segments: List[SpeakerSegment],
        speaker_mapping: Dict[str, str],
        transcript_segments: List[TranscriptSegment],
        output_path: Path,
        ffmpeg_path: Optional[str] = None
    ):
        """
        Create an annotated video with face boxes and speaker labels/subtitles.
        
        Args:
            video_path: Input video path
            frame_data_list: Processed frame data with face detections
            fused_segments: Audio-visual fusion segments
            speaker_mapping: Speaker cluster to name mapping
            transcript_segments: Transcript segments with text
            output_path: Output video path
            ffmpeg_path: Optional path to FFmpeg executable
        """
        logger.info(f"Creating annotated video: {output_path}")
        
        # Open original video
        cap = cv2.VideoCapture(str(video_path))
        if not cap.isOpened():
            raise RuntimeError(f"Could not open video: {video_path}")
        
        # Get video properties
        fps = cap.get(cv2.CAP_PROP_FPS)
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        
        logger.info(f"Video properties: {width}x{height} @ {fps:.2f} FPS, {total_frames} frames")
        
        # Create output video writer
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        temp_output = Path(str(output_path).replace('.mp4', '_temp.mp4'))
        video_writer = cv2.VideoWriter(
            str(temp_output),
            fourcc,
            fps,
            (width, height + self.subtitle_height)  # Add space for subtitles
        )
        
        if not video_writer.isOpened():
            raise RuntimeError(f"Could not open video writer for: {temp_output}")
        
        # Build lookup structures
        speaker_timeline = self._build_speaker_timeline(fused_segments, speaker_mapping)
        transcript_timeline = self._build_transcript_timeline(transcript_segments)
        frame_data_map = {fd.frame_number: fd for fd in frame_data_list}
        
        frame_count = 0
        
        try:
            while True:
                ret, frame = cap.read()
                if not ret:
                    break
                
                # Add subtitle space
                frame_with_subtitle = self._add_subtitle_space(
                    frame, self.subtitle_height
                )
                
                # Add face boxes and labels
                if frame_count in frame_data_map:
                    frame_data = frame_data_map[frame_count]
                    current_time = frame_data.timestamp
                    
                    # Get current speaker and transcript
                    current_speaker = self._get_speaker_at_time(current_time, speaker_timeline)
                    current_text = self._get_transcript_at_time(current_time, transcript_timeline)
                    
                    # Draw face boxes
                    for face in frame_data.faces:
                        frame_with_subtitle = self._draw_face_box(
                            frame_with_subtitle, face
                        )
                    
                    # Draw subtitle
                    frame_with_subtitle = self._draw_subtitle(
                        frame_with_subtitle,
                        current_speaker,
                        current_text,
                        height
                    )
                else:
                    # No face data for this frame, just add subtitle
                    current_time = frame_count / fps
                    current_speaker = self._get_speaker_at_time(current_time, speaker_timeline)
                    current_text = self._get_transcript_at_time(current_time, transcript_timeline)
                    
                    frame_with_subtitle = self._draw_subtitle(
                        frame_with_subtitle,
                        current_speaker,
                        current_text,
                        height
                    )
                
                video_writer.write(frame_with_subtitle)
                
                if (frame_count + 1) % 30 == 0:
                    logger.info(f"Processed {frame_count + 1}/{total_frames} frames")
                
                frame_count += 1
        
        finally:
            cap.release()
            video_writer.release()
        
        logger.info(f"Video annotation complete: {frame_count} frames written")
        
        # Convert temp file to final mp4 with proper codec
        self._finalize_video(temp_output, output_path, ffmpeg_path)
    
    def _add_subtitle_space(
        self,
        frame: np.ndarray,
        subtitle_height: int
    ) -> np.ndarray:
        """Add black space at bottom for subtitles."""
        return cv2.copyMakeBorder(
            frame,
            0, subtitle_height, 0, 0,
            cv2.BORDER_CONSTANT,
            value=self.subtitle_bg_color
        )
    
    def _draw_face_box(
        self,
        frame: np.ndarray,
        face: Face
    ) -> np.ndarray:
        """Draw a face bounding box with confidence indicator."""
        x, y, w, h = face.bbox
        
        # Select color based on confidence
        if face.confidence >= 0.8:
            color = self.high_confidence_color
        elif face.confidence >= 0.6:
            color = self.medium_confidence_color
        else:
            color = self.low_confidence_color
        
        # Draw rectangle
        cv2.rectangle(frame, (x, y), (x + w, y + h), color, 2)
        
        # Draw confidence text
        confidence_text = f"ID:{face.face_id} ({face.confidence:.2f})"
        text_size = cv2.getTextSize(
            confidence_text, self.font, self.font_scale, self.font_thickness
        )[0]
        
        # Draw background for text
        cv2.rectangle(
            frame,
            (x, y - 25),
            (x + text_size[0] + 10, y),
            color,
            -1
        )
        
        # Draw text
        cv2.putText(
            frame,
            confidence_text,
            (x + 5, y - 8),
            self.font,
            self.font_scale,
            (255, 255, 255),
            self.font_thickness
        )
        
        return frame
    
    def _draw_subtitle(
        self,
        frame: np.ndarray,
        speaker: str,
        text: str,
        original_height: int
    ) -> np.ndarray:
        """Draw subtitle text in the bottom area."""
        y_offset = original_height
        
        # Prepare subtitle text
        if speaker and text:
            subtitle = f"{speaker}: {text}"
        elif speaker:
            subtitle = speaker
        elif text:
            subtitle = text
        else:
            subtitle = ""
        
        if not subtitle:
            return frame
        
        # Wrap text if too long
        max_chars_per_line = 80
        lines = []
        for word in subtitle.split(' '):
            if lines and len(lines[-1]) + len(word) + 1 <= max_chars_per_line:
                lines[-1] += ' ' + word
            else:
                lines.append(word)
        
        # Draw each line
        line_height = 30
        for i, line in enumerate(lines[:3]):  # Max 3 lines
            y = y_offset + 20 + (i * line_height)
            
            # Draw text with background
            text_size = cv2.getTextSize(
                line, self.font, self.subtitle_font_scale, self.font_thickness
            )[0]
            
            cv2.rectangle(
                frame,
                (10, y - text_size[1] - 5),
                (20 + text_size[0], y + 5),
                self.subtitle_bg_color,
                -1
            )
            
            cv2.putText(
                frame,
                line,
                (15, y),
                self.font,
                self.subtitle_font_scale,
                self.subtitle_text_color,
                self.font_thickness
            )
        
        return frame
    
    def _build_speaker_timeline(
        self,
        fused_segments: List[SpeakerSegment],
        speaker_mapping: Dict[str, str]
    ) -> List[Tuple[float, float, str]]:
        """Build timeline of (start, end, speaker_name) tuples."""
        timeline = []
        for segment in fused_segments:
            speaker_name = speaker_mapping.get(
                segment.speaker_cluster_id,
                f"Speaker {segment.speaker_cluster_id}"
            )
            timeline.append((segment.start, segment.end, speaker_name))
        
        return sorted(timeline, key=lambda x: x[0])
    
    def _build_transcript_timeline(
        self,
        transcript_segments: List[TranscriptSegment]
    ) -> List[Tuple[float, float, str]]:
        """Build timeline of (start, end, text) tuples."""
        return [
            (seg.start, seg.end, seg.text)
            for seg in sorted(transcript_segments, key=lambda x: x.start)
        ]
    
    def _get_speaker_at_time(
        self,
        current_time: float,
        speaker_timeline: List[Tuple[float, float, str]]
    ) -> str:
        """Get active speaker at given time."""
        for start, end, speaker in speaker_timeline:
            if start <= current_time <= end:
                return speaker
        return ""
    
    def _get_transcript_at_time(
        self,
        current_time: float,
        transcript_timeline: List[Tuple[float, float, str]]
    ) -> str:
        """Get transcript text at given time."""
        for start, end, text in transcript_timeline:
            if start <= current_time <= end:
                return text
        return ""
    
    def _finalize_video(
        self,
        temp_path: Path,
        output_path: Path,
        ffmpeg_path: Optional[str] = None
    ):
        """Convert video to final mp4 format using FFmpeg."""
        try:
            if ffmpeg_path:
                ffmpeg_cmd = ffmpeg_path
            else:
                ffmpeg_cmd = 'ffmpeg'
            
            # Use FFmpeg to re-encode with better codec
            cmd = [
                ffmpeg_cmd,
                '-i', str(temp_path),
                '-c:v', 'libx264',
                '-crf', '23',
                '-c:a', 'aac',
                '-y',
                str(output_path)
            ]
            
            logger.info(f"Running FFmpeg: {' '.join(cmd)}")
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300
            )
            
            if result.returncode != 0:
                logger.warning(f"FFmpeg warning: {result.stderr}")
            
            # Remove temp file
            temp_path.unlink()
            logger.info(f"Annotated video saved: {output_path}")
        
        except Exception as e:
            logger.warning(f"Could not finalize video with FFmpeg: {e}")
            logger.info(f"Keeping temporary video: {temp_path}")
            # Rename temp to final output
            temp_path.rename(output_path)
