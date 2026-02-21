"""Audio-visual fusion module for speaker identification."""

import numpy as np
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
from collections import defaultdict

from ..audio import DiarizationSegment
from ..video import FrameData
from ..utils import get_logger, get_config

logger = get_logger(__name__)


@dataclass
class SpeakerSegment:
    """Represents a fused speaker segment with audio and video alignment."""

    speaker_cluster_id: str
    face_id: Optional[str]
    start: float
    end: float
    confidence_scores: Dict[str, float]

    @property
    def duration(self) -> float:
        """Get segment duration."""
        return self.end - self.start


class AudioVisualFusion:
    """Handles fusion of audio diarization and video face tracking."""

    def __init__(self, config: Optional[Dict] = None):
        """
        Initialize fusion processor.

        Args:
            config: Fusion configuration dictionary
        """
        if config is None:
            config = get_config().get_fusion_config()

        self.config = config
        self.alignment_tolerance = config.get("alignment_tolerance", 0.5)

        # Confidence thresholds
        thresholds = config.get("thresholds", {})
        self.diarization_threshold = thresholds.get("diarization", 0.6)
        self.av_threshold = thresholds.get("av_alignment", 0.5)

        logger.info("AudioVisualFusion initialized")

    def fuse(
        self,
        diarization_segments: List[DiarizationSegment],
        frame_data_list: List[FrameData],
    ) -> List[SpeakerSegment]:
        """
        Fuse audio diarization with video face tracking.

        Args:
            diarization_segments: Audio diarization segments
            frame_data_list: Video frame data with face detections

        Returns:
            List of fused speaker segments
        """
        logger.info(
            f"Fusing {len(diarization_segments)} audio segments with "
            f"{len(frame_data_list)} video frames"
        )

        fused_segments = []

        for diar_seg in diarization_segments:
            # Find frames that overlap with this audio segment
            overlapping_frames = self._get_overlapping_frames(diar_seg, frame_data_list)

            if not overlapping_frames:
                # No video data available - use audio only
                fused_seg = SpeakerSegment(
                    speaker_cluster_id=diar_seg.speaker_id,
                    face_id=None,
                    start=diar_seg.start,
                    end=diar_seg.end,
                    confidence_scores={
                        "diarization": diar_seg.confidence,
                        "av_alignment": 0.0,
                        "face_detection": 0.0,
                    },
                )
                fused_segments.append(fused_seg)
                continue

            # Find most likely speaking face
            face_id, confidence = self._identify_speaking_face(overlapping_frames)

            fused_seg = SpeakerSegment(
                speaker_cluster_id=diar_seg.speaker_id,
                face_id=face_id,
                start=diar_seg.start,
                end=diar_seg.end,
                confidence_scores={
                    "diarization": diar_seg.confidence,
                    "av_alignment": confidence,
                    "face_detection": 1.0 if face_id else 0.0,
                },
            )
            fused_segments.append(fused_seg)

        logger.info(
            f"Created {len(fused_segments)} fused segments, "
            f"{sum(1 for s in fused_segments if s.face_id)} with face IDs"
        )

        return fused_segments

    def _get_overlapping_frames(
        self, segment: DiarizationSegment, frame_data_list: List[FrameData]
    ) -> List[FrameData]:
        """
        Get video frames that overlap with an audio segment.

        Args:
            segment: Audio diarization segment
            frame_data_list: List of all frame data

        Returns:
            List of overlapping frames
        """
        overlapping = []

        for frame_data in frame_data_list:
            # Check if frame timestamp is within segment ± tolerance
            if (
                segment.start - self.alignment_tolerance
                <= frame_data.timestamp
                <= segment.end + self.alignment_tolerance
            ):
                overlapping.append(frame_data)

        return overlapping

    def _identify_speaking_face(
        self, frames: List[FrameData]
    ) -> Tuple[Optional[str], float]:
        """
        Identify which face is most likely speaking across frames.

        Args:
            frames: List of overlapping frames

        Returns:
            Tuple of (face_id, confidence)
        """
        if not frames:
            return None, 0.0

        # Aggregate evidence across frames
        face_scores = defaultdict(float)
        face_counts = defaultdict(int)

        for frame in frames:
            if not frame.faces:
                continue

            # Score each face based on:
            # 1. Lip movement (if available)
            # 2. Face size (central, larger faces more likely)
            # 3. Detection confidence

            for face in frame.faces:
                score = 0.0

                # Lip movement score (most important)
                if face.lip_movement > 0:
                    score += face.lip_movement * 2.0

                # Face size score (larger faces more likely to be speaker)
                # Normalize by frame area
                score += (face.area / 1000000) * 0.5

                # Detection confidence
                score += face.confidence * 0.5

                face_scores[face.face_id] += score
                face_counts[face.face_id] += 1

        if not face_scores:
            return None, 0.0

        # Find face with highest average score
        best_face_id = None
        best_score = 0.0

        for face_id, total_score in face_scores.items():
            avg_score = total_score / face_counts[face_id]
            if avg_score > best_score:
                best_score = avg_score
                best_face_id = face_id

        # Normalize confidence to [0, 1]
        confidence = min(1.0, best_score / 3.0)

        # Only return face if confidence exceeds threshold
        if confidence < self.av_threshold:
            return None, confidence

        return best_face_id, confidence

    def build_speaker_face_mapping(
        self, fused_segments: List[SpeakerSegment]
    ) -> Dict[str, str]:
        """
        Build a mapping from speaker cluster IDs to most common face IDs.

        Args:
            fused_segments: List of fused segments

        Returns:
            Dictionary mapping speaker_cluster_id to face_id
        """
        # Count face occurrences for each speaker
        speaker_faces = defaultdict(lambda: defaultdict(float))

        for segment in fused_segments:
            if segment.face_id:
                # Weight by confidence and duration
                weight = segment.confidence_scores["av_alignment"] * segment.duration
                speaker_faces[segment.speaker_cluster_id][segment.face_id] += weight

        # Select most common face for each speaker
        mapping = {}
        for speaker_id, faces in speaker_faces.items():
            if faces:
                best_face = max(faces.items(), key=lambda x: x[1])[0]
                mapping[speaker_id] = best_face

        logger.info(f"Built speaker-face mapping: {len(mapping)} speakers mapped")

        return mapping

    def get_statistics(self, fused_segments: List[SpeakerSegment]) -> Dict[str, Dict]:
        """
        Calculate statistics for fused segments.

        Args:
            fused_segments: List of fused segments

        Returns:
            Statistics dictionary
        """
        stats = {
            "total_segments": len(fused_segments),
            "segments_with_faces": sum(1 for s in fused_segments if s.face_id),
            "unique_speakers": len(set(s.speaker_cluster_id for s in fused_segments)),
            "unique_faces": len(set(s.face_id for s in fused_segments if s.face_id)),
            "avg_confidence": {
                "diarization": np.mean(
                    [s.confidence_scores["diarization"] for s in fused_segments]
                ),
                "av_alignment": np.mean(
                    [s.confidence_scores["av_alignment"] for s in fused_segments]
                ),
            },
            "total_duration": sum(s.duration for s in fused_segments),
        }

        return stats
