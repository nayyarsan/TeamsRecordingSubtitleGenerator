"""Setup script for Webex Speaker Labeling Tool."""

from setuptools import setup, find_packages
from pathlib import Path

# Read README
readme_file = Path(__file__).parent / "README.md"
long_description = readme_file.read_text() if readme_file.exists() else ""

setup(
    name="webex-speaker-labeling",
    version="0.1.0",
    author="Your Team",
    author_email="your.email@example.com",
    description="Offline speaker labeling for Webex meeting recordings",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/webex-speaker-labeling",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Topic :: Multimedia :: Video",
        "Topic :: Multimedia :: Sound/Audio :: Speech",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
    python_requires=">=3.8",
    install_requires=[
        "numpy>=1.21.0",
        "scipy>=1.7.0",
        "pyannote.audio>=3.0.0",
        "torch>=2.0.0",
        "torchaudio>=2.0.0",
        "librosa>=0.10.0",
        "soundfile>=0.12.0",
        "opencv-python>=4.8.0",
        "opencv-contrib-python>=4.8.0",
        "mediapipe>=0.10.0",
        "pysrt>=1.1.2",
        "webvtt-py>=0.4.6",
        "transformers>=4.30.0",
        "spacy>=3.5.0",
        "jinja2>=3.1.0",
        "click>=8.1.0",
        "pyyaml>=6.0",
        "tqdm>=4.65.0",
        "python-dateutil>=2.8.0",
        "pillow>=10.0.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.4.0",
            "pytest-cov>=4.1.0",
            "black>=23.0.0",
            "flake8>=6.0.0",
            "mypy>=1.4.0",
        ],
        "llm": [
            "openai>=1.0.0",
            "anthropic>=0.18.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "process-meeting=process_meeting:main",
        ],
    },
    include_package_data=True,
    package_data={
        "": ["*.yaml", "*.md"],
    },
)
