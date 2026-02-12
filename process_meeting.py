#!/usr/bin/env python
"""Command-line interface for Webex meeting processing."""

import click
from pathlib import Path
import sys

from src.utils import setup_logger


@click.command()
@click.option(
    "--video",
    type=click.Path(exists=True, path_type=Path),
    required=True,
    help="Path to meeting video file (MP4)",
)
@click.option(
    "--transcript",
    type=click.Path(exists=True, path_type=Path),
    required=False,
    default=None,
    help="Path to transcript file (SRT, VTT, or JSON). If omitted, auto-transcribe.",
)
@click.option(
    "--output-dir",
    type=click.Path(path_type=Path),
    required=True,
    help="Output directory for generated files",
)
@click.option(
    "--asr-model",
    type=str,
    default="base",
    show_default=True,
    help="ASR model size for auto-transcription (tiny, base, small, medium, large)",
)
@click.option(
    "--asr-language",
    type=str,
    default=None,
    help="Optional language code for ASR (e.g., en, fr, es)",
)
@click.option(
    "--ffmpeg-path",
    type=str,
    default=None,
    help="Optional path to ffmpeg executable (if not on PATH)",
)
@click.option(
    "--annotated-video",
    is_flag=True,
    help="Generate annotated video with face detection boxes and speaker labels",
)
@click.option(
    "--web-ui",
    is_flag=True,
    help="Start web UI viewer after processing (localhost:5000)",
)
@click.option(
    "--config",
    type=click.Path(exists=True, path_type=Path),
    default=None,
    help="Path to configuration file (default: config.yaml)",
)
@click.option("--verbose", is_flag=True, help="Enable verbose logging")
@click.version_option(version="0.1.0")
def main(
    video,
    transcript,
    output_dir,
    asr_model,
    asr_language,
    ffmpeg_path,
    annotated_video,
    web_ui,
    config,
    verbose,
):
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
    setup_logger("webex-speaker-labeling", verbose=verbose)

    click.echo("=" * 80)
    click.echo("Webex Meeting Speaker Labeling Tool v0.1.0")
    click.echo("=" * 80)
    click.echo()

    try:
        # Import here to avoid heavy imports when CLI args are invalid
        from src.pipeline import MeetingProcessor

        # Create processor
        processor = MeetingProcessor(config_path=config, verbose=verbose)

        # Process meeting
        output_files = processor.process(
            video_path=video,
            transcript_path=transcript,
            output_dir=output_dir,
            asr_model=asr_model,
            asr_language=asr_language,
            ffmpeg_path=ffmpeg_path,
            generate_annotated_video=annotated_video,
        )

        # Display results
        click.echo()
        click.secho("[OK] Processing completed successfully!", fg="green", bold=True)
        click.echo()
        click.echo("Output files:")
        for file_type, file_path in output_files.items():
            click.echo(f"  - {file_type.upper()}: {file_path}")

        # Start web UI if requested
        if web_ui:
            click.echo()
            click.secho("[INFO] Starting web UI viewer...", fg="cyan", bold=True)

            from src.web_ui import WebUI

            ui = WebUI(output_dir)
            click.echo("Opening web UI at http://localhost:5000")
            click.echo("Press Ctrl+C to stop the server")

            try:
                ui.run(host="0.0.0.0", port=5000, debug=False)
            except KeyboardInterrupt:
                click.echo()
                click.secho("[INFO] Web UI stopped", fg="cyan")

        return 0

    except FileNotFoundError as e:
        click.secho(f"[ERROR] {e}", fg="red", bold=True)
        return 1

    except ValueError as e:
        click.secho(f"[ERROR] {e}", fg="red", bold=True)
        return 1

    except Exception as e:
        click.secho(f"[ERROR] Unexpected error: {e}", fg="red", bold=True)
        if verbose:
            import traceback

            traceback.print_exc()
        return 1


def _render_help() -> str:
    """Render CLI help text without invoking Click's default handlers."""
    ctx = click.Context(main)
    return main.get_help(ctx)


if __name__ == "__main__":
    try:
        sys.exit(main(standalone_mode=False))
    except click.MissingParameter as e:
        click.echo(f"Error: {e}", err=True)
        click.echo(_render_help())
        sys.exit(2)
    except click.ClickException as e:
        click.echo(f"Error: {e}", err=True)
        click.echo(_render_help())
        sys.exit(e.exit_code)
    except Exception as e:
        click.echo(f"Unexpected error: {e}", err=True)
        sys.exit(1)
