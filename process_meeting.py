#!/usr/bin/env python
"""Command-line interface for Webex meeting processing."""

import click
from pathlib import Path
import sys

from src.pipeline import MeetingProcessor
from src.utils import setup_logger


@click.command()
@click.option(
    '--video',
    type=click.Path(exists=True, path_type=Path),
    required=True,
    help='Path to meeting video file (MP4)'
)
@click.option(
    '--transcript',
    type=click.Path(exists=True, path_type=Path),
    required=True,
    help='Path to transcript file (SRT, VTT, or JSON)'
)
@click.option(
    '--output-dir',
    type=click.Path(path_type=Path),
    required=True,
    help='Output directory for generated files'
)
@click.option(
    '--config',
    type=click.Path(exists=True, path_type=Path),
    default=None,
    help='Path to configuration file (default: config.yaml)'
)
@click.option(
    '--verbose',
    is_flag=True,
    help='Enable verbose logging'
)
@click.version_option(version='0.1.0')
def main(video, transcript, output_dir, config, verbose):
    """
    Process Webex meeting recordings to identify and label speakers.
    
    This tool performs:
    1. Audio diarization to identify when each speaker talks
    2. Video face detection and tracking
    3. Audio-visual fusion to match voices with faces
    4. Speaker name extraction from introductions
    5. Generation of labeled subtitles and metadata
    
    Example:
    
        python process_meeting.py \\
            --video meeting.mp4 \\
            --transcript meeting.vtt \\
            --output-dir ./output
    """
    # Setup logging
    setup_logger('webex-speaker-labeling', verbose=verbose)
    
    click.echo("=" * 80)
    click.echo("Webex Meeting Speaker Labeling Tool v0.1.0")
    click.echo("=" * 80)
    click.echo()
    
    try:
        # Create processor
        processor = MeetingProcessor(
            config_path=config,
            verbose=verbose
        )
        
        # Process meeting
        output_files = processor.process(
            video_path=video,
            transcript_path=transcript,
            output_dir=output_dir
        )
        
        # Display results
        click.echo()
        click.secho("✓ Processing completed successfully!", fg='green', bold=True)
        click.echo()
        click.echo("Output files:")
        for file_type, file_path in output_files.items():
            click.echo(f"  • {file_type.upper()}: {file_path}")
        
        return 0
        
    except FileNotFoundError as e:
        click.secho(f"✗ Error: {e}", fg='red', bold=True)
        return 1
        
    except ValueError as e:
        click.secho(f"✗ Error: {e}", fg='red', bold=True)
        return 1
        
    except Exception as e:
        click.secho(f"✗ Unexpected error: {e}", fg='red', bold=True)
        if verbose:
            import traceback
            traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())
