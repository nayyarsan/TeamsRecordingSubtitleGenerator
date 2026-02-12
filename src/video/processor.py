"""Video processing module for face detection and tracking."""

import cv2
import numpy as np
import mediapipe as mp
from pathlib import Path
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
from collections import defaultdict

from ..utils import get_logger, get_config

logger = get_logger(__name__)


@dataclass
class Face:
    """Represents a detected face in a frame."""

    face_id: str
    bbox: Tuple[int, int, int, int]  # (x, y, w, h)
    confidence: float
    landmarks: Optional[np.ndarray] = None
    lip_movement: float = 0.0

    @property
    def center(self) -> Tuple[int, int]:
        """Get face center coordinates."""
        x, y, w, h = self.bbox
        return (x + w // 2, y + h // 2)

    @property
    def area(self) -> int:
        """Get face bounding box area."""
        _, _, w, h = self.bbox
        return w * h


@dataclass
class FrameData:
    """Represents processed data for a single frame."""

    timestamp: float
    frame_number: int
    faces: List[Face]


class VideoProcessor:
    """Handles video processing, face detection, and tracking."""

    def __init__(self, config: Optional[Dict] = None):
        """
        Initialize video processor.

        Args:
            config: Video configuration dictionary
        """
        if config is None:
            config = get_config().get_video_config()

        self.config = config
        self.fps = config.get("fps", 3)

        # Face detection config
        face_config = config.get("face_detection", {})
        self.min_confidence = face_config.get("min_confidence", 0.5)
        self.min_face_size = face_config.get("min_face_size", 0.05)
        self.max_faces = face_config.get("max_faces", 10)

        # Lip detection config
        lip_config = config.get("lip_detection", {})
        self.lip_enabled = lip_config.get("enabled", True)
        self.lip_window_size = lip_config.get("window_size", 5)
        self.lip_threshold = lip_config.get("movement_threshold", 0.1)

        # Initialize MediaPipe Face Detection
        if not hasattr(mp, "solutions"):
            raise ImportError(
                "mediapipe.solutions is not available. Install a compatible "
                "MediaPipe package (for example: pip install mediapipe==0.10.11)."
            )

        self.mp_face_detection = mp.solutions.face_detection
        self.mp_face_mesh = mp.solutions.face_mesh

        self.face_detector = None
        self.face_mesh = None

        # Face tracking state
        self.face_tracks = {}
        self.next_face_id = 0
        self.face_history = defaultdict(list)

        logger.info("VideoProcessor initialized")

    def _initialize_detectors(self):
        """Initialize MediaPipe detectors."""
        if self.face_detector is None:
            self.face_detector = self.mp_face_detection.FaceDetection(
                model_selection=1,  # Full range detection
                min_detection_confidence=self.min_confidence,
            )

        if self.lip_enabled and self.face_mesh is None:
            self.face_mesh = self.mp_face_mesh.FaceMesh(
                static_image_mode=False,
                max_num_faces=self.max_faces,
                refine_landmarks=True,
                min_detection_confidence=self.min_confidence,
                min_tracking_confidence=0.5,
            )

    def process_video(self, video_path: Path) -> List[FrameData]:
        """
        Process video and extract face data.

        Args:
            video_path: Path to video file

        Returns:
            List of frame data with detected faces
        """
        logger.info(f"Processing video: {video_path}")

        self._initialize_detectors()

        # Open video
        cap = cv2.VideoCapture(str(video_path))

        if not cap.isOpened():
            raise RuntimeError(f"Could not open video: {video_path}")

        # Get video properties
        original_fps = cap.get(cv2.CAP_PROP_FPS)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        duration = total_frames / original_fps

        logger.info(
            f"Video: {original_fps:.2f} FPS, {total_frames} frames, {duration:.2f}s"
        )

        # Calculate frame sampling interval
        frame_interval = max(1, int(original_fps / self.fps))

        frame_data_list = []
        frame_count = 0
        processed_count = 0

        try:
            while True:
                ret, frame = cap.read()
                if not ret:
                    break

                # Process only sampled frames
                if frame_count % frame_interval == 0:
                    timestamp = frame_count / original_fps

                    # Detect faces
                    faces = self._detect_faces(frame, timestamp)

                    # Track faces across frames
                    tracked_faces = self._track_faces(faces, timestamp)

                    # Detect lip movement
                    if self.lip_enabled:
                        tracked_faces = self._detect_lip_movement(
                            frame, tracked_faces, timestamp
                        )

                    frame_data = FrameData(
                        timestamp=timestamp,
                        frame_number=frame_count,
                        faces=tracked_faces,
                    )
                    frame_data_list.append(frame_data)

                    processed_count += 1

                    if processed_count % 100 == 0:
                        logger.info(
                            f"Processed {processed_count} frames "
                            f"({frame_count}/{total_frames})"
                        )

                frame_count += 1

        finally:
            cap.release()

        logger.info(
            f"Video processing complete: {len(frame_data_list)} frames processed, "
            f"{len(self.face_tracks)} unique faces detected"
        )

        return frame_data_list

    def _detect_faces(self, frame: np.ndarray, timestamp: float) -> List[Face]:
        """
        Detect faces in a frame.

        Args:
            frame: Video frame
            timestamp: Frame timestamp

        Returns:
            List of detected faces
        """
        # Convert BGR to RGB for MediaPipe
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        # Run face detection
        results = self.face_detector.process(rgb_frame)

        faces = []

        if results.detections:
            h, w, _ = frame.shape
            min_size = int(h * self.min_face_size)

            for detection in results.detections:
                # Get bounding box
                bbox = detection.location_data.relative_bounding_box
                x = int(bbox.xmin * w)
                y = int(bbox.ymin * h)
                width = int(bbox.width * w)
                height = int(bbox.height * h)

                # Filter by size
                if width < min_size or height < min_size:
                    continue

                # Create face object (ID will be assigned during tracking)
                face = Face(
                    face_id="temp",  # Temporary ID
                    bbox=(x, y, width, height),
                    confidence=detection.score[0],
                )
                faces.append(face)

        return faces

    def _track_faces(self, faces: List[Face], timestamp: float) -> List[Face]:
        """
        Track faces across frames using simple IoU matching.

        Args:
            faces: Detected faces in current frame
            timestamp: Frame timestamp

        Returns:
            List of tracked faces with assigned IDs
        """
        # Get active tracks (seen in recent frames)
        active_tracks = {
            fid: track
            for fid, track in self.face_tracks.items()
            if timestamp - track["last_seen"] < 1.0  # 1 second threshold
        }

        # Match faces to tracks using IoU
        matched_faces = []
        matched_track_ids = set()

        for face in faces:
            best_match = None
            best_iou = 0.3  # Minimum IoU threshold

            for track_id, track in active_tracks.items():
                if track_id in matched_track_ids:
                    continue

                iou = self._calculate_iou(face.bbox, track["bbox"])
                if iou > best_iou:
                    best_iou = iou
                    best_match = track_id

            if best_match:
                # Update existing track
                face.face_id = best_match
                self.face_tracks[best_match].update(
                    {
                        "bbox": face.bbox,
                        "last_seen": timestamp,
                        "count": self.face_tracks[best_match]["count"] + 1,
                    }
                )
                matched_track_ids.add(best_match)
            else:
                # Create new track
                face_id = f"face_{self.next_face_id}"
                face.face_id = face_id
                self.face_tracks[face_id] = {
                    "bbox": face.bbox,
                    "first_seen": timestamp,
                    "last_seen": timestamp,
                    "count": 1,
                }
                self.next_face_id += 1

            # Store in history
            self.face_history[face.face_id].append((timestamp, face))
            matched_faces.append(face)

        return matched_faces

    def _detect_lip_movement(
        self, frame: np.ndarray, faces: List[Face], timestamp: float
    ) -> List[Face]:
        """
        Detect lip movement for speaking detection.

        Args:
            frame: Video frame
            faces: List of detected faces
            timestamp: Frame timestamp

        Returns:
            List of faces with lip movement scores
        """
        if not faces:
            return faces

        # Convert to RGB
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        # Run face mesh
        results = self.face_mesh.process(rgb_frame)

        if results.multi_face_landmarks:
            h, w, _ = frame.shape

            for idx, face in enumerate(faces):
                if idx >= len(results.multi_face_landmarks):
                    break

                landmarks = results.multi_face_landmarks[idx]

                # Extract lip landmarks (simplified)
                # Upper lip: 61, 62, 63
                # Lower lip: 291, 292, 293
                lip_indices = [61, 62, 63, 291, 292, 293]

                lip_points = []
                for lip_idx in lip_indices:
                    lm = landmarks.landmark[lip_idx]
                    lip_points.append((lm.x * w, lm.y * h))

                # Calculate lip movement (distance between upper and lower lip)
                upper_lip_center = np.mean(lip_points[:3], axis=0)
                lower_lip_center = np.mean(lip_points[3:], axis=0)
                lip_distance = np.linalg.norm(upper_lip_center - lower_lip_center)

                # Get historical lip distances
                history = [
                    f.lip_movement
                    for ts, f in self.face_history[face.face_id][
                        -self.lip_window_size :
                    ]
                    if f.face_id == face.face_id
                ]

                if history:
                    # Normalize by recent average
                    avg_distance = np.mean(history)
                    if avg_distance > 0:
                        normalized_movement = lip_distance / avg_distance - 1.0
                        face.lip_movement = max(0, normalized_movement)
                    else:
                        face.lip_movement = 0
                else:
                    face.lip_movement = 0

        return faces

    @staticmethod
    def _calculate_iou(
        bbox1: Tuple[int, int, int, int], bbox2: Tuple[int, int, int, int]
    ) -> float:
        """
        Calculate Intersection over Union for two bounding boxes.

        Args:
            bbox1: First bounding box (x, y, w, h)
            bbox2: Second bounding box (x, y, w, h)

        Returns:
            IoU score
        """
        x1, y1, w1, h1 = bbox1
        x2, y2, w2, h2 = bbox2

        # Calculate intersection
        x_left = max(x1, x2)
        y_top = max(y1, y2)
        x_right = min(x1 + w1, x2 + w2)
        y_bottom = min(y1 + h1, y2 + h2)

        if x_right < x_left or y_bottom < y_top:
            return 0.0

        intersection = (x_right - x_left) * (y_bottom - y_top)

        # Calculate union
        area1 = w1 * h1
        area2 = w2 * h2
        union = area1 + area2 - intersection

        if union == 0:
            return 0.0

        return intersection / union

    def get_face_statistics(self) -> Dict[str, Dict]:
        """
        Get statistics for all tracked faces.

        Returns:
            Dictionary mapping face_id to statistics
        """
        stats = {}

        for face_id, track in self.face_tracks.items():
            duration = track["last_seen"] - track["first_seen"]
            stats[face_id] = {
                "first_seen": track["first_seen"],
                "last_seen": track["last_seen"],
                "duration": duration,
                "frame_count": track["count"],
            }

        return stats
