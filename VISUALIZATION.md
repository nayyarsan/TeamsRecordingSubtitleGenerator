# Visualization Features Guide

This guide covers the face detection and subtitle visualization features in the Webex Speaker Labeling Tool.

## Overview

The tool provides three ways to visualize and interact with speaker labeling results:

1. **React Web Application** (Recommended): Modern web interface with video upload, real-time processing, interactive workspace
2. **Annotated Video**: An MP4 video file with face detection boxes and speaker labels overlaid
3. **Legacy Web UI Viewer**: Flask-based interface to browse and watch processed videos

---

## React Web Application (Recommended)

### Overview

The primary web interface is a modern React application with FastAPI backend, providing a complete workflow from video upload to speaker management and export.

**Technology Stack:**
- **Frontend**: React 18 + Vite + Tailwind CSS + React Router
- **Backend**: FastAPI + Uvicorn + SSE (Server-Sent Events)
- **Deployment**: Single server serving both API and React app

### Starting the Application

**Production Mode** (serves built React app):
```bash
python run_server.py
# Access at: http://localhost:8000
```

**Development Mode** (hot reload for frontend changes):
```bash
# Terminal 1: Backend
python run_server.py

# Terminal 2: Frontend
cd frontend
npm run dev
# Access at: http://localhost:3000 (proxies API to port 8000)
```

### Features

#### Dashboard Page (`/`)

**File Upload:**
- Drag-and-drop or click to upload video files
- Supported formats: MP4, MKV, AVI, MOV
- Real-time upload progress bar
- File size and validation feedback

**Processing Configuration:**
- **ASR Model**: Select Whisper model size (tiny, base, small, medium, large)
  - Recommendation: `base` for fastest processing, `medium` for best accuracy
- **Max Speakers**: Set expected number of speakers (default: 10)
- **Ollama Model** (Optional): Select local LLM model for AI-assisted name extraction
  - Requires Ollama running locally
  - Shows connection status and available models

**Real-Time Processing:**
- Live progress updates via Server-Sent Events (SSE)
- 4-step pipeline visualization:
  1. Audio Processing (diarization + transcription)
  2. Video Processing (face detection + tracking)
  3. Audio-Visual Fusion (speaker-face alignment)
  4. Name Extraction (AI-assisted intro analysis)
- System logs with color-coded levels (info, warning, error)
- Processing typically takes 1-3x video duration on CPU

**Processed Videos List:**
- Browse all previously processed videos
- Shows video name, timestamp, speaker count
- Click to open in workspace

---

#### Workspace Page (`/workspace/:videoId`)

The workspace provides an interactive environment for reviewing, editing, and exporting results.

**Layout:**
- **Left**: Video player with face overlay and subtitles
- **Right**: Sidebar with Timeline and Speakers tabs
- **Top Menu**: File, Export, Show/Hide Faces

##### Video Player

**Playback Controls:**
- Play/pause, seek scrubber, volume control
- Keyboard shortcuts:
  - Space: Play/pause
  - Arrow keys: Seek forward/backward
- Playback speed control (0.5x to 2x)

**Face Overlay:**
- Real-time face bounding boxes synchronized with video
- Color-coded by detection confidence:
  - Green: High (≥80%)
  - Orange: Medium (60-80%)
  - Red: Low (<60%)
- Shows speaker labels and face IDs
- Toggle visibility with "Show/Hide Faces" button

**Subtitle Display:**
- Live subtitles at bottom of video
- Shows speaker name and text
- Syncs automatically with video playback

##### Timeline Inspector (Right Sidebar - Timeline Tab)

**Features:**
- Scrollable list of all subtitle segments
- Each segment displays:
  - Timestamp (MM:SS format)
  - Speaker name badge (color-coded)
  - Text preview (truncated for long segments)
- **Active segment highlighting**: Currently playing segment is highlighted with blue border
- **Click-to-seek**: Click any segment to jump video to that timestamp
- **Auto-scroll**: Timeline auto-scrolls to keep active segment visible

**Use Cases:**
- Quick navigation through long videos
- Find specific speakers or topics
- Review subtitle accuracy

##### Speaker Manager (Right Sidebar - Speakers Tab)

**Features:**
- List of all detected speakers
- Each speaker shows:
  - Current name (from AI extraction or "Speaker N" fallback)
  - Name confidence score (if AI-extracted)
  - Total speaking time
  - Number of segments

**Rename Speakers:**
1. Click edit button next to speaker name
2. Enter new name in input field
3. Click save
4. SRT file regenerates automatically with new name
5. Video refreshes to show updated subtitles

**AI Name Suggestions:**
- Click "Suggest Names" button
- Ollama analyzes intro segments for name mentions
- Shows suggested names with confidence scores
- Click to apply suggestion to matching speaker
- Requires Ollama running locally with a model loaded

##### Export Modal

**Export Formats:**

1. **SRT Subtitles** (`.srt`)
   - Standard SubRip format
   - Includes speaker labels
   - Compatible with all video players
   - Use for: Adding subtitles to videos, archiving transcripts

2. **JSON Metadata** (`.json`)
   - Complete structured data
   - Includes: segments, speakers, timestamps, confidence scores
   - Use for: Programmatic access, data analysis, custom integrations

3. **Annotated Video** (`.mp4`)
   - Video with face boxes and subtitles baked in
   - H.264 codec for compatibility
   - Use for: Sharing, presentations, archiving annotated results

**Export Process:**
- Select format from modal
- Click Export button
- File downloads automatically
- Success/error feedback displayed

---

### Architecture Details

#### Backend API Endpoints

The FastAPI backend provides REST endpoints at `/api`:

**Upload & Processing:**
- `POST /api/upload` - Upload video file
- `POST /api/process` - Start processing pipeline
- `GET /api/process/status/{video_id}` - SSE stream for real-time progress

**Video Data:**
- `GET /api/videos` - List all processed videos
- `GET /api/video/{id}/metadata` - Get video metadata and speakers
- `GET /api/video/{id}/subtitles` - Get parsed SRT as JSON
- `GET /api/video/{id}/faces` - Get frame-by-frame face detection data
- `GET /api/video/{id}/annotated` - Serve annotated video file
- `GET /api/video/{id}/original` - Serve original video file

**Speaker Management:**
- `POST /api/video/{id}/speakers/{speaker_id}/rename` - Rename speaker
- `POST /api/video/{id}/suggest-names` - AI name suggestions via Ollama

**Export:**
- `POST /api/video/{id}/export` - Export SRT/JSON/video

**System:**
- `GET /api/ollama/status` - Check Ollama connectivity
- `GET /api/ollama/models` - List available Ollama models
- `GET /api/system/info` - System and GPU information

#### Frontend Architecture

**Component Structure:**
```
src/
├── api/
│   └── client.js               # API wrapper with error handling
├── components/
│   ├── common/
│   │   ├── Button.jsx          # Reusable button component
│   │   ├── Modal.jsx          # Generic modal wrapper
│   │   └── StatusBadge.jsx     # Status indicators
│   ├── dashboard/
│   │   ├── DashboardPage.jsx   # Main dashboard
│   │   ├── DropZone.jsx        # File upload
│   │   ├── ConfigPanel.jsx     # Processing config
│   │   ├── PipelineProgress.jsx # SSE progress display
│   │   └── SystemLogs.jsx      # Real-time logs
│   ├── workspace/
│   │   ├── WorkspacePage.jsx   # Main workspace layout
│   │   ├── VideoPlayer.jsx     # Video player with overlays
│   │   ├── FaceOverlay.jsx     # Canvas face bounding boxes
│   │   ├── SubtitleOverlay.jsx # Subtitle display
│   │   ├── PlayerControls.jsx  # Playback controls
│   │   ├── TimelineInspector.jsx # Timeline sidebar
│   │   ├── SpeakerManager.jsx  # Speaker list sidebar
│   │   └── ExportModal.jsx     # Export dialog
│   └── layout/
│       ├── Header.jsx          # Top navigation
│       └── Sidebar.jsx         # Sidebar wrapper
├── hooks/
│   ├── useSSE.js               # Server-Sent Events hook
│   ├── useVideoSync.js         # Video/subtitle sync
│   └── useFaceOverlay.js       # Canvas face rendering
├── utils/
│   └── formatters.js           # Time/date/bytes formatters
├── App.jsx                     # Routes: /, /workspace/:id
├── main.jsx                    # React entry point
└── index.css                   # Tailwind + custom styles
```

**State Management:**
- React hooks (useState, useEffect, useRef) for local state
- No Redux/Context - simple prop drilling suffices for this app
- SSE for real-time server updates

**Styling:**
- Tailwind CSS utility classes
- Dark theme with custom color palette
- Responsive design (desktop-first, 1024px+ optimal)

#### Data Flow

**Upload & Process:**
```
User uploads file → POST /api/upload → File saved to ./uploads/
User starts process → POST /api/process → Background thread runs pipeline
Frontend connects SSE → GET /api/process/status/{id} → Real-time updates
Process completes → Output files in ./output/ → Dashboard refreshes
```

**Workspace:**
```
User opens workspace → GET /api/video/{id}/{metadata,subtitles,faces}
Video player loads → useVideoSync hook tracks current time
Face overlay renders → Canvas draws boxes from face data JSON
Timeline updates → Active segment follows video playback
User renames speaker → POST rename → SRT regenerates → Data refreshes
User exports → POST export → File downloads via browser
```

---

### Browser Compatibility

**Supported Browsers:**
- Chrome/Edge 90+ (Recommended)
- Firefox 88+
- Safari 14+

**Requirements:**
- Modern ES6+ JavaScript support
- HTML5 video/canvas support
- WebSocket/SSE support (for real-time updates)
- localStorage (for UI preferences)

**Known Issues:**
- Safari may have video playback quirks with certain codecs
- Older browsers may not support canvas drawing performance optimizations

---

### Development

**Setup:**
```bash
# Install frontend dependencies
cd frontend
npm install

# Install backend dependencies
pip install -e ".[dev]"
```

**Running Locally:**
```bash
# Backend (terminal 1)
python run_server.py

# Frontend with hot reload (terminal 2)
cd frontend
npm run dev
```

**Build for Production:**
```bash
cd frontend
npm run build
# Output: frontend/dist/

# Backend will serve frontend/dist/ automatically
python run_server.py
# Access at: http://localhost:8000
```

**Linting & Formatting:**
```bash
# Backend
black src/
flake8 src/
mypy src/

# Frontend
cd frontend
npm run lint  # If configured
```

---

### Troubleshooting

**Problem**: "Cannot connect to backend"
- **Solution**: Ensure `run_server.py` is running on port 8000
- **Check**: `curl http://localhost:8000/api/videos`

**Problem**: "Video won't play"
- **Cause**: Browser codec incompatibility
- **Solution**: Use Chrome/Edge, or convert video to H.264/AAC

**Problem**: "Face overlay not showing"
- **Cause**: Face detection data not generated during processing
- **Solution**: Reprocess with face detection enabled in config

**Problem**: "Ollama suggestions fail"
- **Cause**: Ollama not running or no models installed
- **Solution**: Start Ollama (`ollama serve`) and pull a model (`ollama pull llama2`)

**Problem**: "Upload fails"
- **Cause**: File too large or unsupported format
- **Solution**: Check file size (<2GB recommended), use MP4/MKV/AVI

**Problem**: "SSE progress not updating"
- **Cause**: Browser closed SSE connection
- **Solution**: Refresh page, check browser console for errors

---

## Annotated Video Output

### Generating Annotated Videos

To generate an annotated video with face detection boxes and speaker labels, use the `--annotated-video` flag:

```bash
python process_meeting.py \
    --video meeting.mp4 \
    --output-dir ./output \
    --ffmpeg-path "C:\path\to\ffmpeg.exe" \
    --annotated-video
```

### What's Included in Annotated Videos

The annotated video includes:

1. **Face Detection Boxes**
   - Green boxes: High confidence (≥80%)
   - Orange boxes: Medium confidence (60-80%)
   - Red boxes: Low confidence (<60%)
   - Shows face ID and confidence score

2. **Speaker Labels and Subtitles**
   - Speaker name matched from introductions
   - Current transcript text
   - Displayed at the bottom of the frame
   - Updates in real-time as audio plays

3. **Synchronized Timing**
   - Face boxes match exact detection timestamps
   - Subtitles sync with audio segments
   - Consistent frame rate with source video

### Output Files

When generating an annotated video, you get:

```
output/
├── video_name_labeled.srt          # Subtitles with speaker labels
├── video_name_labeled.json         # Metadata (speakers, segments, timing)
└── video_name_annotated.mp4        # Video with face boxes and subtitles
```

### Technical Details

- **Output Resolution**: Same as input video
- **Codec**: H.264 (libx264) for compatibility
- **Format**: MP4 with AAC audio
- **Processing**: ~3x real-time (varies with video resolution)

## Web UI Viewer

### Starting the Web UI

**Option 1: During Processing**

```bash
python process_meeting.py \
    --video meeting.mp4 \
    --output-dir ./output \
    --annotated-video \
    --web-ui
```

The UI will automatically start after processing completes.

**Option 2: View Existing Results**

```bash
python view_videos.py --output-dir ./output --port 5000
```

### Web UI Features

#### Video Selection
- **List View**: Browse all processed videos on the left
- **Timestamps**: See when each video was processed
- **Sort Order**: Most recent videos appear first

#### Player Tab
- **HTML5 Video Player**: Standard video controls
  - Play/pause
  - Seek/timeline
  - Volume control
  - Full screen
  - Playback speed

- **Live Subtitle Display**: Real-time subtitle synchronization
  - Shows current speaker and transcript text
  - Updates as you play the video
  - Automatically syncs to video position

#### Metadata Tab
- **Video Statistics**: Duration, resolution, FPS
- **Speaker Information**: All detected speakers
- **Segment Count**: Total number of speaker segments
- **Speaker Badges**: Visual display of all identified speakers

### Web UI Access

Once started, access the UI at:

```
http://localhost:5000
```

Default configuration:
- **Host**: 0.0.0.0 (accessible from any network)
- **Port**: 5000
- **Debug Mode**: Disabled (production)

To stop the server: Press `Ctrl+C` in the terminal

### Customizing the Web UI

Modify the port when starting:

```bash
python view_videos.py --output-dir ./output --port 8080
```

This allows running multiple instances or avoiding port conflicts.

## Face Detection Details

### How Face Detection Works

The pipeline uses **MediaPipe Face Detection** (powered by BlazeFace):

1. Frame Sampling: Processes video at ~3 FPS
2. Detection: Identifies face bounding boxes
3. Tracking: Assigns consistent IDs across frames
4. Lip Detection: Measures lip movement for speaker activity

### Interpreting Face Boxes

- **Box Color Indicates Confidence**
  - Green: High-quality face detection (≥80% confidence)
  - Orange: Medium quality (60-80%), may need manual review
  - Red: Low confidence (<60%), likely false positive

- **Face ID**: Persistent identifier for tracking
  - Same person should have consistent ID
  - IDs reset on major scene changes
  - Used for audio-visual fusion

### Configuring Face Detection

Face detection settings in `config.yaml`:

```yaml
video:
  face_detection:
    min_confidence: 0.5         # Minimum detection confidence
    min_face_size: 0.05         # Minimum face size (0-1, relative to frame)
    max_faces: 10               # Maximum faces per frame
  
  lip_detection:
    enabled: true               # Enable lip movement detection
    window_size: 5              # Frames to average for smoothing
    movement_threshold: 0.1     # Minimum movement to register activity
```

## Subtitle Synchronization

### How Subtitles Are Synchronized

1. **Audio Processing**: Diarization creates speaker segments with timings
2. **Speech Recognition**: Whisper transcribes audio to text segments
3. **Fusion**: Matches speaker segments to transcript segments
4. **Overlay**: Renders subtitles synchronized with video frames

### Subtitle Format (SRT Example)

```
1
00:00:01,500 --> 00:00:05,000
John Smith: Good morning everyone, thanks for joining.

2
00:00:05,500 --> 00:00:10,000
Sarah Johnson: Happy to be here. Let's get started.
```

## Performance Considerations

### Annotated Video Generation

- **Processing Speed**: ~3x real-time on CPU
  - Fast: ~30 min video = ~10 min processing
  - Variables: video resolution, codec, face complexity

- **File Sizes**
  - Source quality typically preserved
  - Slight increase due to annotation overlays
  - Example: 100MB input → 110-120MB annotated output

### Web UI

- **Streaming**: Videos stream from disk (no transcoding)
- **Responsive**: Works on desktop and tablets
- **Container Requirements**: 
  - ~100MB per video file
  - Minimal disk I/O for UI operations
  - No database required

## Troubleshooting

### Annotated Video Issues

**Problem**: "Could not open video writer"
- **Solution**: Check FFmpeg installation and path
- **Check**: `ffmpeg -version` in terminal

**Problem**: Missing faces in annotated video
- **Solution**: May be too small, far from camera, or obscured
- **Adjust**: Lower `min_face_size` in config.yaml

**Problem**: Colors/text cuts off
- **Solution**: Video resolution too small
- **Minimum**: 640x480 recommended for readability

### Web UI Issues

**Problem**: "Address already in use"
- **Solution**: Use different port: `python view_videos.py --port 8080`
- **Check**: `netstat -an | findstr :5000` to find conflicting process

**Problem**: Video won't play
- **Check**: Codec compatibility in browser
- **Try**: Using Chrome, Edge, or Firefox
- **Fallback**: Download and play locally with VLC

**Problem**: Subtitles out of sync
- **Cause**: Different frame rates or audio offset
- **Solution**: Check SRT file timing manually
- **Alternative**: Check JSON metadata for segment times

## Advanced Usage

### Batch Processing with Visualization

Create a batch script to process multiple videos:

```bash
# batch_process.ps1
$videos = Get-ChildItem ".\input\*.mp4"

foreach ($video in $videos) {
    python process_meeting.py `
        --video $video.FullName `
        --output-dir ./output `
        --ffmpeg-path $env:FFMPEG_PATH `
        --annotated-video
}

# View all results
python view_videos.py --output-dir ./output
```

### Custom Subtitle Styling

Modify subtitle appearance by editing `src/visualizer.py`:

```python
# Change colors
self.font_color = (255, 0, 0)  # BGR format: Blue, Green, Red
self.subtitle_text_color = (0, 255, 0)  # Green text

# Adjust font size
self.font_scale = 0.8  # Larger or smaller text
self.font_thickness = 2  # Bolder or thinner
```

### Extracting Frames from Annotated Video

Using FFmpeg to extract specific frames:

```bash
ffmpeg -i output/video_annotated.mp4 \
    -vf "select=eq(n\,1000)" \
    -vsync vfr \
    frame_%04d.png
```

## API Integration

### Using VideoVisualizer Programmatically

```python
from src.visualizer import VideoVisualizer
from pathlib import Path

visualizer = VideoVisualizer()

# Generate annotated video
visualizer.create_annotated_video(
    video_path=Path("input.mp4"),
    frame_data_list=frame_data,
    fused_segments=segments,
    speaker_mapping={"speaker_0": "John"},
    transcript_segments=transcripts,
    output_path=Path("output_annotated.mp4"),
    ffmpeg_path="C:\\path\\to\\ffmpeg.exe"
)
```

### Using WebUI Programmatically

```python
from src.web_ui import WebUI
from pathlib import Path

ui = WebUI(Path("output"))
ui.run(host='127.0.0.1', port=8080, debug=True)
```

## Next Steps

1. **Generate Annotated Videos**: Add `--annotated-video` to your processing
2. **View Results**: Use the web UI with `--web-ui` or `view_videos.py`
3. **Customize Output**: Adjust face detection and subtitle settings
4. **Share Results**: Embed annotated videos in presentations or reports
5. **Integrate**: Use visualizer classes in your own applications

## Performance Tips

1. **Reduce Video Resolution**: Lower quality = faster processing
2. **Process Shorter Clips**: Test on small videos first
3. **Disable Lip Detection**: Set `lip_detection.enabled: false` for speed
4. **Pre-compress**: Use Hardware acceleration if available
5. **Cache Results**: Store output videos for reuse

## Notes

- Face detection confidence varies with lighting, angle, and occlusion
- Subtitle timing accuracy depends on diarization and speech recognition quality
- Web UI requires modern browser (Chrome 90+, Firefox 88+, Safari 14+)
- Windows/Linux/Mac compatible for both annotated video and web UI

