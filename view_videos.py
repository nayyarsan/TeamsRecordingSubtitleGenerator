#!/usr/bin/env python
"""Standalone web UI viewer for processed videos."""

import click
from pathlib import Path
import sys

from src.web_ui import WebUI


@click.command()
@click.option(
    "--output-dir",
    type=click.Path(exists=True, path_type=Path),
    required=True,
    help="Directory containing annotated videos and metadata",
)
@click.option(
    "--host",
    type=str,
    default="0.0.0.0",
    show_default=True,
    help="Host to bind web server to",
)
@click.option(
    "--port",
    type=int,
    default=5000,
    show_default=True,
    help="Port to run web server on",
)
@click.version_option(version="0.1.0")
def main(output_dir, host, port):
    """
    Start web UI viewer for processed meeting videos.

    This UI allows you to:
    - View annotated videos with face detection boxes
    - See synchronized subtitles with speaker labels
    - Browse speaker metadata and statistics

    Example:

        python view_videos.py --output-dir ./output --port 5000

    Then open http://localhost:5000 in your browser
    """
    click.echo("=" * 80)
    click.echo("Webex Speaker Labeling - Video Viewer v0.1.0")
    click.echo("=" * 80)
    click.echo()

    try:
        ui = WebUI(output_dir)

        click.secho(f"Starting web UI on http://{host}:{port}", fg="green", bold=True)
        click.echo("Press Ctrl+C to stop the server")
        click.echo()

        ui.run(host=host, port=port, debug=False)

    except KeyboardInterrupt:
        click.echo()
        click.secho("[INFO] Web UI stopped", fg="cyan")
        return 0

    except Exception as e:
        click.secho(f"[ERROR] {e}", fg="red", bold=True)
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
