"""Speaker naming module for extracting participant names."""

import re
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass

from ..audio import TranscriptSegment
from ..fusion import SpeakerSegment
from ..utils import get_logger, get_config

logger = get_logger(__name__)


@dataclass
class NamedSpeaker:
    """Represents a speaker with assigned name."""

    speaker_cluster_id: str
    name: str
    confidence: float
    face_id: Optional[str] = None


class SpeakerNamer:
    """Handles extraction and assignment of speaker names."""

    def __init__(self, config: Optional[Dict] = None):
        """
        Initialize speaker namer.

        Args:
            config: Naming configuration dictionary
        """
        if config is None:
            config = get_config().get_naming_config()

        self.config = config

        # Introduction detection config
        intro_config = config.get("intro_detection", {})
        self.max_intro_time = intro_config.get("max_intro_time", 300)
        self.min_intro_duration = intro_config.get("min_intro_duration", 2.0)
        self.intro_patterns = intro_config.get(
            "intro_patterns",
            ["I'm", "I am", "My name is", "This is", "Hi, I'm", "Hello, I'm"],
        )

        # LLM config (optional)
        llm_config = config.get("llm", {})
        self.llm_enabled = llm_config.get("enabled", False)

        logger.info("SpeakerNamer initialized")

    def extract_names(
        self,
        transcript_segments: List[TranscriptSegment],
        fused_segments: List[SpeakerSegment],
    ) -> List[NamedSpeaker]:
        """
        Extract speaker names from transcript and map to speaker clusters.

        Args:
            transcript_segments: Transcript segments
            fused_segments: Fused audio-visual segments

        Returns:
            List of named speakers
        """
        logger.info("Extracting speaker names from transcript")

        # Extract introduction segments
        intro_segments = self._extract_intro_segments(transcript_segments)

        # Parse names from introductions
        name_candidates = self._parse_names_from_intros(intro_segments)

        # Map names to speaker clusters
        named_speakers = self._map_names_to_clusters(
            name_candidates, intro_segments, fused_segments, transcript_segments
        )

        # Fill in missing names with defaults
        all_speakers = set(s.speaker_cluster_id for s in fused_segments)
        named_ids = set(ns.speaker_cluster_id for ns in named_speakers)

        missing_speakers = all_speakers - named_ids
        for idx, speaker_id in enumerate(sorted(missing_speakers)):
            # Find face_id for this speaker
            face_id = None
            for seg in fused_segments:
                if seg.speaker_cluster_id == speaker_id and seg.face_id:
                    face_id = seg.face_id
                    break

            named_speakers.append(
                NamedSpeaker(
                    speaker_cluster_id=speaker_id,
                    name=f"Speaker {idx + len(named_speakers) + 1}",
                    confidence=0.0,
                    face_id=face_id,
                )
            )

        logger.info(
            f"Named {len(named_speakers)} speakers: "
            f"{[ns.name for ns in named_speakers]}"
        )

        return named_speakers

    def _extract_intro_segments(
        self, transcript_segments: List[TranscriptSegment]
    ) -> List[TranscriptSegment]:
        """
        Extract introduction portions from transcript.

        Args:
            transcript_segments: All transcript segments

        Returns:
            List of introduction segments
        """
        intro_segments = []

        for segment in transcript_segments:
            # Only consider segments in the intro time window
            if segment.start > self.max_intro_time:
                break

            # Check if segment is long enough
            if segment.duration < self.min_intro_duration:
                continue

            # Check if segment contains introduction patterns
            text_lower = segment.text.lower()
            if any(pattern.lower() in text_lower for pattern in self.intro_patterns):
                intro_segments.append(segment)

        logger.info(f"Found {len(intro_segments)} potential introduction segments")
        return intro_segments

    def _parse_names_from_intros(
        self, intro_segments: List[TranscriptSegment]
    ) -> List[Tuple[str, float, str]]:
        """
        Parse names from introduction segments.

        Args:
            intro_segments: Introduction segments

        Returns:
            List of (name, confidence, original_text) tuples
        """
        name_candidates = []

        # Common name extraction patterns
        patterns = [
            r"(?:I'm|I am|My name is)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)",
            r"(?:This is|Hi,?\s*I'm|Hello,?\s*I'm)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)",
            r"([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\s+(?:here|speaking)",
        ]

        for segment in intro_segments:
            for pattern in patterns:
                matches = re.finditer(pattern, segment.text)
                for match in matches:
                    name = match.group(1).strip()

                    # Validate name (simple heuristics)
                    if self._is_valid_name(name):
                        confidence = 0.8  # Base confidence for pattern match
                        name_candidates.append((name, confidence, segment.text))
                        logger.debug(
                            f"Found name candidate: '{name}' in '{segment.text[:50]}...'"
                        )

        return name_candidates

    def _is_valid_name(self, name: str) -> bool:
        """
        Validate if extracted string is likely a real name.

        Args:
            name: Candidate name string

        Returns:
            True if likely a valid name
        """
        # Basic validation
        if len(name) < 2 or len(name) > 50:
            return False

        # Should start with capital letter
        if not name[0].isupper():
            return False

        # Should not be a common word (expanded list)
        common_words = {
            "Today",
            "Yesterday",
            "Tomorrow",
            "Everyone",
            "Everybody",
            "Please",
            "Thank",
            "Thanks",
            "Welcome",
            "Good",
            "Morning",
            "Afternoon",
            "Evening",
            "Meeting",
            "Team",
            "All",
        }
        if name in common_words:
            return False

        return True

    def _map_names_to_clusters(
        self,
        name_candidates: List[Tuple[str, float, str]],
        intro_segments: List[TranscriptSegment],
        fused_segments: List[SpeakerSegment],
        transcript_segments: List[TranscriptSegment],
    ) -> List[NamedSpeaker]:
        """
        Map extracted names to speaker cluster IDs.

        Args:
            name_candidates: List of name candidates
            intro_segments: Introduction transcript segments
            fused_segments: Fused audio-visual segments
            transcript_segments: All transcript segments

        Returns:
            List of named speakers
        """
        named_speakers = []
        used_clusters = set()

        for name, confidence, original_text in name_candidates:
            # Find transcript segment containing this name
            intro_seg = None
            for seg in intro_segments:
                if original_text in seg.text:
                    intro_seg = seg
                    break

            if not intro_seg:
                continue

            # Find fused segment that overlaps with this introduction
            speaker_id = self._find_speaker_for_intro(intro_seg, fused_segments)

            if speaker_id and speaker_id not in used_clusters:
                # Find face_id for this speaker
                face_id = None
                for seg in fused_segments:
                    if seg.speaker_cluster_id == speaker_id and seg.face_id:
                        face_id = seg.face_id
                        break

                named_speakers.append(
                    NamedSpeaker(
                        speaker_cluster_id=speaker_id,
                        name=name,
                        confidence=confidence,
                        face_id=face_id,
                    )
                )
                used_clusters.add(speaker_id)

        return named_speakers

    def _find_speaker_for_intro(
        self, intro_segment: TranscriptSegment, fused_segments: List[SpeakerSegment]
    ) -> Optional[str]:
        """
        Find which speaker cluster corresponds to an introduction segment.

        Args:
            intro_segment: Introduction transcript segment
            fused_segments: Fused audio-visual segments

        Returns:
            Speaker cluster ID or None
        """
        # Find fused segments that overlap with this intro
        overlapping = []

        for seg in fused_segments:
            # Check for temporal overlap
            if not (seg.end < intro_segment.start or seg.start > intro_segment.end):
                overlapping.append(seg)

        if not overlapping:
            return None

        # Return the speaker with most overlap
        best_speaker = max(
            overlapping,
            key=lambda s: min(s.end, intro_segment.end)
            - max(s.start, intro_segment.start),
        )

        return best_speaker.speaker_cluster_id

    def create_speaker_mapping(
        self, named_speakers: List[NamedSpeaker]
    ) -> Dict[str, str]:
        """
        Create a simple mapping from speaker cluster IDs to names.

        Args:
            named_speakers: List of named speakers

        Returns:
            Dictionary mapping speaker_cluster_id to name
        """
        return {ns.speaker_cluster_id: ns.name for ns in named_speakers}
