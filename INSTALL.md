# Installation Guide

## Prerequisites

- Python 3.8 or higher
- FFmpeg (for audio extraction)
- ~4GB RAM minimum
- ~10GB disk space for dependencies

## Step 1: Install System Dependencies

### Ubuntu/Debian
```bash
sudo apt-get update
sudo apt-get install -y python3 python3-pip python3-venv ffmpeg
```

### macOS
```bash
brew install python ffmpeg
```

### Windows
1. Install Python from [python.org](https://python.org)
2. Install FFmpeg from [ffmpeg.org](https://ffmpeg.org/download.html)
3. Add FFmpeg to PATH

## Step 2: Clone Repository

```bash
git clone <repository-url>
cd webex-speaker-labeling
```

## Step 3: Create Virtual Environment

```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

## Step 4: Install Python Dependencies

```bash
# Upgrade pip
pip install --upgrade pip

# Install package
pip install -e .
```

This will install all required dependencies from `requirements.txt`.

## Step 5: Setup PyAnnote Models

The tool uses PyAnnote Audio for speaker diarization. You need a HuggingFace token:

1. Create a free account at [huggingface.co](https://huggingface.co)
2. Get your token from [Settings > Access Tokens](https://huggingface.co/settings/tokens)
3. Accept the user agreement for PyAnnote models:
   - Visit [pyannote/speaker-diarization-3.1](https://huggingface.co/pyannote/speaker-diarization-3.1)
   - Click "Agree and access repository"

4. Set your token as an environment variable:

```bash
# Linux/macOS
export HF_TOKEN="your_token_here"

# Or add to ~/.bashrc or ~/.zshrc for persistence
echo 'export HF_TOKEN="your_token_here"' >> ~/.bashrc

# Windows (PowerShell)
$env:HF_TOKEN="your_token_here"

# Windows (Command Prompt)
set HF_TOKEN=your_token_here
```

## Step 6: Download Spacy Language Model (Optional)

If using NLP features for name extraction:

```bash
python -m spacy download en_core_web_sm
```

## Verify Installation

```bash
# Check Python version
python --version  # Should be 3.8+

# Check FFmpeg
ffmpeg -version

# Test the tool
python process_meeting.py --help
```

## Troubleshooting

### PyTorch Installation Issues

If PyTorch installation fails, install it separately first:

```bash
# CPU only (recommended for MVP)
pip install torch torchaudio --index-url https://download.pytorch.org/whl/cpu
```

### OpenCV Issues

If OpenCV import fails:

```bash
pip uninstall opencv-python opencv-contrib-python
pip install opencv-python opencv-contrib-python
```

### MediaPipe Issues

On some systems, MediaPipe may require additional dependencies:

```bash
# Linux
sudo apt-get install -y libgl1-mesa-glx

# macOS
# Usually no additional dependencies needed
```

### FFmpeg Not Found

Ensure FFmpeg is in your PATH:

```bash
which ffmpeg  # Linux/macOS
where ffmpeg  # Windows
```

### Memory Issues

If processing fails with memory errors:
- Close other applications
- Process shorter meetings first
- Reduce video sampling FPS in `config.yaml`

## Development Installation

For development with testing and linting tools:

```bash
pip install -e ".[dev]"
```

## Optional: LLM Integration

For optional LLM-assisted name extraction:

```bash
pip install -e ".[llm]"
```

Then configure in `config.yaml` and set API keys:

```bash
export OPENAI_API_KEY="your_openai_key"
# or
export ANTHROPIC_API_KEY="your_anthropic_key"
```

## Uninstallation

```bash
pip uninstall webex-speaker-labeling
```

## Getting Help

If you encounter issues:
1. Check the logs (use `--verbose` flag)
2. Verify all dependencies are installed correctly
3. Check GitHub issues
4. Open a new issue with error details
