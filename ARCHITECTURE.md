# Architecture Overview

## System Design

The Webex Speaker Labeling Tool follows a modular pipeline architecture with clear separation of concerns:

```
Input (Video + Transcript)
         ↓
    ┌────────────────────────────────┐
    │   MeetingProcessor (Pipeline)  │
    └────────────────────────────────┘
         ↓
    ┌────────────┬──────────────┐
    │   Audio    │    Video     │
    │ Processing │  Processing  │
    └────────────┴──────────────┘
         ↓              ↓
         └──────┬───────┘
                ↓
        ┌───────────────┐
        │  Audio-Visual │
        │    Fusion     │
        └───────────────┘
                ↓
        ┌───────────────┐
        │    Speaker    │
        │    Naming     │
        └───────────────┘
                ↓
        ┌───────────────┐
        │    Output     │
        │  Generation   │
        └───────────────┘
         ↓
Output (SRT + JSON)
```

## Module Descriptions

### 1. Audio Module (`src/audio/`)

**Purpose**: Extract and analyze audio tracks

**Components**:
- `AudioProcessor`: Extracts audio from video and performs diarization
- `TranscriptParser`: Parses transcript files (SRT, VTT, JSON)

**Key Technologies**:
- FFmpeg: Audio extraction
- PyAnnote Audio: Speaker diarization
- PyTorch: Deep learning backend

**Data Flow**:
```
Video File → FFmpeg → Audio File → PyAnnote → Diarization Segments
Transcript File → Parser → Transcript Segments
```

### 2. Video Module (`src/video/`)

**Purpose**: Detect and track faces in video

**Components**:
- `VideoProcessor`: Face detection, tracking, and lip movement analysis

**Key Technologies**:
- OpenCV: Video processing and frame extraction
- MediaPipe: Face detection and facial landmarks
- Custom tracking: IoU-based face tracking across frames

**Data Flow**:
```
Video File → Frame Sampling → Face Detection → Face Tracking → Frame Data
                                    ↓
                              Lip Movement Detection
```

### 3. Fusion Module (`src/fusion/`)

**Purpose**: Combine audio and video information

**Components**:
- `AudioVisualFusion`: Aligns diarization with face detections

**Algorithm**:
1. Temporal alignment: Match audio segments to video frames
2. Speaker identification: Use lip movement and face prominence
3. Confidence scoring: Aggregate evidence across frames

**Data Flow**:
```
Diarization Segments + Frame Data → Temporal Alignment
                                          ↓
                                   Face Scoring
                                          ↓
                                  Fused Segments
```

### 4. Naming Module (`src/naming/`)

**Purpose**: Extract speaker names from transcript

**Components**:
- `SpeakerNamer`: Identifies introductions and maps names to speakers

**Algorithm**:
1. Extract introduction segments (first N minutes)
2. Pattern matching for "I'm...", "My name is...", etc.
3. Temporal alignment with speaker segments
4. Fallback to generic labels

**Data Flow**:
```
Transcript Segments → Intro Extraction → Name Parsing
                                              ↓
Fused Segments → Speaker Mapping ← Name-to-Cluster Mapping
```

### 5. Output Module (`src/output/`)

**Purpose**: Generate final output files

**Components**:
- `OutputGenerator`: Creates SRT and JSON outputs

**Formats**:
- **SRT**: Standard subtitle format with speaker labels
- **JSON**: Structured metadata for programmatic access

## Data Structures

### DiarizationSegment
```python
@dataclass
class DiarizationSegment:
    speaker_id: str        # Cluster ID (e.g., "spk_0")
    start: float           # Start time in seconds
    end: float            # End time in seconds
    confidence: float      # Diarization confidence
```

### TranscriptSegment
```python
@dataclass
class TranscriptSegment:
    start: float           # Start time
    end: float            # End time
    text: str             # Transcript text
    speaker: Optional[str] # Original speaker label
```

### Face
```python
@dataclass
class Face:
    face_id: str                    # Tracking ID
    bbox: Tuple[int, int, int, int] # Bounding box
    confidence: float               # Detection confidence
    lip_movement: float            # Speaking activity score
```

### FrameData
```python
@dataclass
class FrameData:
    timestamp: float    # Frame timestamp
    frame_number: int   # Frame index
    faces: List[Face]   # Detected faces
```

### SpeakerSegment (Fused)
```python
@dataclass
class SpeakerSegment:
    speaker_cluster_id: str            # Audio cluster
    face_id: Optional[str]             # Video face
    start: float
    end: float
    confidence_scores: Dict[str, float] # Multi-modal confidence
```

### NamedSpeaker
```python
@dataclass
class NamedSpeaker:
    speaker_cluster_id: str
    name: str                    # Human-readable name
    confidence: float            # Name extraction confidence
    face_id: Optional[str]
```

## Configuration System

The tool uses a hierarchical YAML configuration:

```yaml
audio:           # Audio processing settings
  sample_rate
  diarization:
    max_speakers
    min_segment_duration

video:           # Video processing settings
  fps
  face_detection:
    min_confidence
  lip_detection:
    enabled

fusion:          # Fusion settings
  alignment_tolerance
  thresholds:
    diarization
    av_alignment

naming:          # Name extraction settings
  intro_detection:
    max_intro_time
  llm:
    enabled

output:          # Output generation settings
  srt:
    max_line_length
  json:
    pretty_print

processing:      # General processing settings
  num_workers
  cleanup_temp
```

## Performance Considerations

### CPU Optimization
- Frame sampling: Process every Nth frame (configurable FPS)
- PyAnnote CPU mode: Forced CPU execution
- Efficient tracking: IoU-based tracking without deep features
- Batch processing: Minimize file I/O

### Memory Management
- Streaming: Process video frame-by-frame
- Temporary files: Cleaned up after processing
- Lazy loading: Diarization pipeline loaded only when needed

### Scalability
- Current: Up to 10 speakers, 2-hour meetings
- Bottlenecks: Diarization (1-2x real-time), video processing (0.5-1x)
- Future: GPU support, parallel processing

## Extension Points

### 1. Adding New Transcript Formats
```python
# In src/audio/transcript.py
@staticmethod
def parse_new_format(file_path: Path) -> List[TranscriptSegment]:
    # Implement parser
    pass
```

### 2. Custom Face Detectors
```python
# In src/video/processor.py
def _detect_faces_custom(self, frame: np.ndarray) -> List[Face]:
    # Implement custom detector
    pass
```

### 3. LLM Integration
```python
# In src/naming/extractor.py
def _extract_names_with_llm(self, intro_text: str) -> List[str]:
    # Call LLM API
    pass
```

### 4. Additional Output Formats
```python
# In src/output/generator.py
def generate_custom_format(self, segments, output_path):
    # Generate custom output
    pass
```

## Testing Strategy

### Unit Tests
- Test each module independently
- Mock external dependencies (FFmpeg, models)
- Test edge cases (no faces, no speakers, etc.)

### Integration Tests
- Test full pipeline with sample data
- Verify output format correctness
- Check performance benchmarks

### End-to-End Tests
- Process real meeting recordings
- Validate against ground truth
- Measure accuracy metrics

## Error Handling

### Graceful Degradation
1. **No faces detected**: Fall back to audio-only labeling
2. **No introductions found**: Use generic speaker labels
3. **Diarization failure**: Return error with diagnostics

### Logging
- Info: Major pipeline stages
- Debug: Detailed processing steps
- Warning: Potential issues (low confidence)
- Error: Failures with stack traces

## Privacy & Security

### Local Processing
- All processing happens on user's machine
- No data sent to external services (by default)
- Optional LLM features clearly marked and disabled by default

### Data Handling
- Temporary files in configurable directory
- Automatic cleanup after processing
- No telemetry or usage tracking

## Future Enhancements

### Short-term
- GPU acceleration support
- Real-time processing capability
- Manual speaker name override
- Web UI for easier access

### Medium-term
- VS Code extension
- Electron desktop app
- Batch processing automation
- Advanced name extraction (organizational context)

### Long-term
- Multi-room support
- Multi-language support
- Cloud deployment option
- Webex marketplace integration
