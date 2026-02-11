# Webex Meeting Speaker Labeling Tool (MVP)

An offline Python tool that post-processes Webex meeting recordings to identify and label speakers using audio diarization and video analysis.

## Features

- **Audio Diarization**: Identifies distinct speakers from audio tracks
- **Video Analysis**: Detects faces and tracks lip movements to associate speakers with visual identities
- **Speaker Naming**: Automatically extracts participant names from meeting introductions
- **Multi-format Output**: Generates labeled SRT subtitles and structured JSON metadata
- **CPU-Optimized**: Runs locally without GPU requirements
- **Privacy-First**: All processing happens on your machine

## Use Cases

- Post-process Webex meetings recorded in conference rooms (single microphone, multiple participants)
- Generate accurate speaker-labeled transcripts
- Create searchable meeting records with speaker attribution

## System Requirements

- Python 3.8+
- CPU-based processing (no GPU required)
- ~4GB RAM for typical meetings
- Disk space for temporary processing files

## Installation

```bash
# Clone the repository
git clone <repository-url>
cd webex-speaker-labeling

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

## Quick Start

```bash
python process_meeting.py \
  --video path/to/meeting.mp4 \
  --transcript path/to/transcript.vtt \
  --output-dir ./output
```

## Output Files

- **meeting_labeled.srt**: Subtitle file with speaker names
- **meeting_labeled.json**: Structured metadata with speaker segments, timestamps, and confidence scores

## Project Structure

```
webex-speaker-labeling/
├── src/
│   ├── audio/           # Audio processing and diarization
│   ├── video/           # Face detection and tracking
│   ├── fusion/          # Audio-visual alignment
│   ├── naming/          # Speaker name extraction
│   └── output/          # Output generation
├── process_meeting.py   # Main CLI entry point
├── config.yaml          # Configuration parameters
└── requirements.txt     # Python dependencies
```

## Configuration

Edit `config.yaml` to customize:
- Video frame sampling rate
- Diarization parameters
- Face detection thresholds
- Name extraction patterns

## Limitations (MVP)

- Up to 10 participants
- Meeting duration up to 2 hours
- Processing time: ~1-2x meeting duration
- Best results when all participants are visible on camera
- Single-room, single-microphone setups

## Future Enhancements

- VS Code extension integration
- Electron desktop app wrapper
- Real-time processing capabilities
- GPU acceleration support

## Privacy & Security

- **100% Local Processing**: No data leaves your machine by default
- **Optional Cloud Services**: Can be configured but disabled by default
- **No Data Collection**: No telemetry or usage tracking

## License

[Your License Here]

## Contributing

Contributions welcome! Please read CONTRIBUTING.md for guidelines.

## Support

For issues or questions, please open a GitHub issue.
