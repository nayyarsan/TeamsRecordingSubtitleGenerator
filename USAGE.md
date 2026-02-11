# Usage Examples

## Basic Usage

Process a meeting with default settings:

```bash
python process_meeting.py \
  --video meeting.mp4 \
  --transcript meeting.vtt \
  --output-dir ./output
```

## Verbose Mode

Get detailed progress information:

```bash
python process_meeting.py \
  --video meeting.mp4 \
  --transcript meeting.vtt \
  --output-dir ./output \
  --verbose
```

## Custom Configuration

Use a custom configuration file:

```bash
python process_meeting.py \
  --video meeting.mp4 \
  --transcript meeting.vtt \
  --output-dir ./output \
  --config my_config.yaml
```

## Supported File Formats

### Video Files
- MP4 (recommended)
- AVI
- MOV
- MKV

### Transcript Files
- VTT (WebVTT)
- SRT (SubRip)
- JSON (custom format)

## Example Workflows

### 1. Basic Conference Room Meeting

You have a 30-minute meeting with 5 participants all in one room:

```bash
# Process the meeting
python process_meeting.py \
  --video conference_room_2024.mp4 \
  --transcript conference_room_2024.vtt \
  --output-dir ./processed_meetings/2024_q1

# Output will be:
# ./processed_meetings/2024_q1/conference_room_2024_labeled.srt
# ./processed_meetings/2024_q1/conference_room_2024_labeled.json
```

### 2. Long Meeting (90 minutes)

For longer meetings, processing may take 1-2x the meeting duration:

```bash
python process_meeting.py \
  --video quarterly_review.mp4 \
  --transcript quarterly_review.vtt \
  --output-dir ./quarterly_reviews \
  --verbose  # Track progress
```

### 3. Processing Multiple Meetings

Batch process several meetings:

```bash
#!/bin/bash
# batch_process.sh

for video in meetings/*.mp4; do
    base=$(basename "$video" .mp4)
    echo "Processing $base..."
    
    python process_meeting.py \
        --video "$video" \
        --transcript "transcripts/${base}.vtt" \
        --output-dir "processed/${base}"
done
```

### 4. Custom Settings for Better Accuracy

Adjust settings in `config.yaml` for your specific needs:

```yaml
# config_high_quality.yaml
video:
  fps: 5  # Sample more frames (slower but more accurate)
  
  face_detection:
    min_confidence: 0.7  # Higher threshold for face detection
  
  lip_detection:
    enabled: true
    movement_threshold: 0.08  # More sensitive lip detection

fusion:
  alignment_tolerance: 0.3  # Stricter time alignment

naming:
  intro_detection:
    max_intro_time: 600  # Check first 10 minutes for intros
```

Then use it:

```bash
python process_meeting.py \
  --video important_meeting.mp4 \
  --transcript important_meeting.vtt \
  --output-dir ./output \
  --config config_high_quality.yaml
```

## Output Files

### SRT Subtitle File

Format:
```
1
00:00:10,500 --> 00:00:15,000
John Smith: Thanks everyone for joining today's meeting.

2
00:00:15,200 --> 00:00:20,500
Sarah Johnson: Happy to be here. Let's discuss the Q1 results.
```

Use cases:
- Add as subtitles to video
- Create searchable meeting records
- Generate meeting minutes

### JSON Metadata File

Format:
```json
{
  "metadata": {
    "total_segments": 145,
    "total_speakers": 5,
    "duration": 1847.3
  },
  "speakers": [
    {
      "name": "John Smith",
      "speaker_cluster_id": "spk_0",
      "face_id": "face_0",
      "name_confidence": 0.850
    }
  ],
  "segments": [
    {
      "speaker_name": "John Smith",
      "speaker_cluster_id": "spk_0",
      "face_id": "face_0",
      "start": 10.5,
      "end": 15.0,
      "text": "Thanks everyone for joining today's meeting.",
      "confidence": {
        "diarization": 0.92,
        "av_alignment": 0.78,
        "face_detection": 1.0
      }
    }
  ]
}
```

Use cases:
- Further analysis with custom tools
- Import into databases
- Generate visualizations
- Build search interfaces

## Integration Examples

### 1. Python Script Integration

```python
from pathlib import Path
from src.pipeline import process_meeting

# Process a meeting
output_files = process_meeting(
    video_path="meeting.mp4",
    transcript_path="meeting.vtt",
    output_dir="./output",
    verbose=True
)

# Access output files
print(f"SRT: {output_files['srt']}")
print(f"JSON: {output_files['json']}")

# Parse JSON output
import json
with open(output_files['json']) as f:
    data = json.load(f)
    
print(f"Total speakers: {data['metadata']['total_speakers']}")
for speaker in data['speakers']:
    print(f"  - {speaker['name']}")
```

### 2. Jupyter Notebook

```python
# notebook.ipynb
from src.pipeline import MeetingProcessor
import json
import pandas as pd

# Process meeting
processor = MeetingProcessor(verbose=True)
outputs = processor.process(
    Path("meeting.mp4"),
    Path("meeting.vtt"),
    Path("./output")
)

# Load and analyze results
with open(outputs['json']) as f:
    data = json.load(f)

# Create dataframe
df = pd.DataFrame(data['segments'])

# Analysis
print("Speaker statistics:")
print(df.groupby('speaker_name')['text'].count())

print("\nAverage speaking duration:")
df['duration'] = df['end'] - df['start']
print(df.groupby('speaker_name')['duration'].mean())
```

### 3. Add Subtitles to Video

```bash
# Using ffmpeg to burn subtitles into video
ffmpeg -i meeting.mp4 \
  -vf "subtitles=output/meeting_labeled.srt" \
  meeting_with_subtitles.mp4
```

## Performance Tips

### 1. Reduce Video Sampling Rate

In `config.yaml`:
```yaml
video:
  fps: 2  # Instead of 3 (faster)
```

### 2. Process Shorter Segments

Split long meetings:
```bash
# Split 2-hour meeting into 30-minute chunks
ffmpeg -i long_meeting.mp4 -c copy -t 00:30:00 part1.mp4
ffmpeg -i long_meeting.mp4 -c copy -ss 00:30:00 -t 00:30:00 part2.mp4
# ... process each part separately
```

### 3. Use Lower Quality Video

If processing is too slow:
```bash
# Reduce video resolution before processing
ffmpeg -i high_res_meeting.mp4 \
  -vf scale=640:480 \
  -c:a copy \
  low_res_meeting.mp4
```

## Troubleshooting Common Issues

### No Speakers Detected

If diarization fails to detect speakers:
1. Check audio quality
2. Verify multiple people are speaking
3. Try adjusting diarization thresholds in config

### Incorrect Speaker Labels

If speaker names are wrong:
1. Check if introductions occur in first 5 minutes
2. Verify intro patterns match your meeting format
3. Manually specify names (feature coming soon)

### Low Confidence Scores

If confidence scores are low:
1. Ensure good video quality (faces visible)
2. Check audio quality (clear speech)
3. Adjust thresholds in config.yaml

## Advanced Configuration

See `config.yaml` for all available options.

Key settings to tune:
- `video.fps`: Trade speed for accuracy
- `face_detection.min_confidence`: Face detection threshold
- `fusion.alignment_tolerance`: Audio-video sync tolerance
- `naming.intro_detection.max_intro_time`: How long to search for intros
