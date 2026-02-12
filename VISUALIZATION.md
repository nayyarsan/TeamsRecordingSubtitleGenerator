# Visualization Features Guide

This guide covers the face detection and subtitle visualization features in the Webex Speaker Labeling Tool.

## Overview

The tool provides two ways to visualize the speaker labeling results:

1. **Annotated Video**: An MP4 video file with face detection boxes and speaker labels overlaid
2. **Web UI Viewer**: An interactive web interface to browse and watch processed videos

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

