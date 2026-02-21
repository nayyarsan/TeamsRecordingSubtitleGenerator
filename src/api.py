"""FastAPI backend for MediaProcessor UI."""

import json
import uuid
import asyncio
import threading
from pathlib import Path
from typing import Dict

from fastapi import FastAPI, UploadFile, File, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from sse_starlette.sse import EventSourceResponse

from .utils import get_logger

logger = get_logger(__name__)

# In-memory state for active processing jobs
_jobs: Dict[str, dict] = {}
_processors: Dict[str, object] = {}


def create_app(output_dir: str = "./output", upload_dir: str = "./uploads") -> FastAPI:
    """Create and configure the FastAPI application."""

    output_path = Path(output_dir)
    upload_path = Path(upload_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    upload_path.mkdir(parents=True, exist_ok=True)

    app = FastAPI(title="MediaProcessor API", version="1.0.0")

    # CORS for React dev server
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3000", "http://localhost:5173"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # --- Upload ---
    @app.post("/api/upload")
    async def upload_file(file: UploadFile = File(...)):
        """Upload a media file."""
        if not file.filename:
            raise HTTPException(400, "No file provided")

        ext = Path(file.filename).suffix.lower()
        allowed = {".mp4", ".mkv", ".avi", ".mov", ".mp3", ".wav"}
        if ext not in allowed:
            raise HTTPException(
                400, f"Unsupported format: {ext}. Allowed: {', '.join(allowed)}"
            )

        video_id = Path(file.filename).stem + "_" + uuid.uuid4().hex[:8]
        safe_name = video_id + ext
        dest = upload_path / safe_name

        with open(dest, "wb") as f:
            while chunk := await file.read(1024 * 1024):
                f.write(chunk)

        logger.info(f"Uploaded file: {dest}")
        return {
            "video_id": video_id,
            "filename": safe_name,
            "size": dest.stat().st_size,
        }

    # --- Process ---
    @app.post("/api/process")
    async def start_processing(request: Request):
        """Start processing a video with given config."""
        body = await request.json()
        video_id = body.get("video_id")
        if not video_id:
            raise HTTPException(400, "video_id required")

        # Find uploaded file
        upload_file_path = None
        for f in upload_path.iterdir():
            if f.stem.startswith(video_id) or f.stem == video_id:
                upload_file_path = f
                break

        if not upload_file_path or not upload_file_path.exists():
            raise HTTPException(404, f"Upload not found for video_id: {video_id}")

        config = {
            "asr_model": body.get("asr_model", "base"),
            "max_speakers": body.get("max_speakers", 10),
            "ollama_model": body.get("ollama_model"),
            "generate_annotated_video": body.get("generate_annotated_video", True),
        }

        # Initialize job state
        _jobs[video_id] = {
            "status": "running",
            "step": "initializing",
            "percent": 0,
            "logs": [],
            "error": None,
        }

        # Run processing in background thread
        thread = threading.Thread(
            target=_run_processing,
            args=(video_id, upload_file_path, output_path, config),
            daemon=True,
        )
        thread.start()

        return {"video_id": video_id, "status": "started"}

    @app.get("/api/process/status/{video_id}")
    async def process_status_sse(video_id: str):
        """SSE stream for processing progress."""
        if video_id not in _jobs:
            raise HTTPException(404, "No job found for this video_id")

        async def event_generator():
            last_log_index = 0
            while True:
                job = _jobs.get(video_id)
                if not job:
                    yield {
                        "event": "error",
                        "data": json.dumps({"message": "Job not found"}),
                    }
                    break

                # Send new log entries
                logs = job.get("logs", [])
                new_logs = logs[last_log_index:]
                last_log_index = len(logs)

                data = {
                    "step": job["step"],
                    "percent": job["percent"],
                    "status": job["status"],
                    "logs": new_logs,
                }

                if job.get("error"):
                    data["error"] = job["error"]

                yield {"event": "progress", "data": json.dumps(data)}

                if job["status"] in ("complete", "error"):
                    break

                await asyncio.sleep(1)

        return EventSourceResponse(event_generator())

    # --- Videos ---
    @app.get("/api/videos")
    async def list_videos():
        """List all processed videos."""
        videos = []
        if output_path.exists():
            for json_file in output_path.glob("*_labeled.json"):
                base_name = json_file.stem.replace("_labeled", "")
                stat = json_file.stat()
                try:
                    with open(json_file) as f:
                        data = json.load(f)
                    speaker_count = data.get("metadata", {}).get("total_speakers", 0)
                except Exception:
                    speaker_count = 0

                videos.append(
                    {
                        "id": base_name,
                        "name": base_name,
                        "timestamp": stat.st_mtime,
                        "speaker_count": speaker_count,
                    }
                )

        return {"videos": sorted(videos, key=lambda x: x["timestamp"], reverse=True)}

    @app.get("/api/video/{video_id}/metadata")
    async def get_metadata(video_id: str):
        """Get video metadata."""
        json_file = output_path / f"{video_id}_labeled.json"
        if not json_file.exists():
            raise HTTPException(404, "Video not found")

        with open(json_file) as f:
            data = json.load(f)

        metadata = data.get("metadata", {})
        speakers = data.get("speakers", [])
        segments = data.get("segments", [])

        speaker_names = list(
            set(seg.get("speaker_name", "Unknown") for seg in segments)
        )

        return {
            "duration": metadata.get("duration", 0),
            "speaker_count": metadata.get("total_speakers", len(speaker_names)),
            "speakers": speakers,
            "speaker_names": speaker_names,
            "segment_count": metadata.get("total_segments", len(segments)),
        }

    @app.get("/api/video/{video_id}/subtitles")
    async def get_subtitles(video_id: str):
        """Get parsed SRT as JSON."""
        srt_file = output_path / f"{video_id}_labeled.srt"
        if not srt_file.exists():
            return {"subtitles": []}

        subtitles = _parse_srt(srt_file)
        return {"subtitles": subtitles}

    @app.get("/api/video/{video_id}/faces")
    async def get_faces(video_id: str):
        """Get per-frame face bounding box data."""
        faces_file = output_path / f"{video_id}_faces.json"
        if not faces_file.exists():
            return {"video_resolution": [0, 0], "frames": []}

        with open(faces_file) as f:
            data = json.load(f)
        return data

    @app.post("/api/video/{video_id}/speakers/{speaker_id}/rename")
    async def rename_speaker(video_id: str, speaker_id: str, request: Request):
        """Rename a speaker and regenerate SRT."""
        body = await request.json()
        new_name = body.get("name")
        if not new_name:
            raise HTTPException(400, "name required")

        json_file = output_path / f"{video_id}_labeled.json"
        if not json_file.exists():
            raise HTTPException(404, "Video not found")

        with open(json_file) as f:
            data = json.load(f)

        # Update speaker name in speakers list
        for speaker in data.get("speakers", []):
            if speaker.get("speaker_cluster_id") == speaker_id:
                speaker["name"] = new_name

        # Update speaker name in segments
        for seg in data.get("segments", []):
            if seg.get("speaker_cluster_id") == speaker_id:
                seg["speaker_name"] = new_name

        with open(json_file, "w") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        # Regenerate SRT
        _regenerate_srt(data, output_path / f"{video_id}_labeled.srt")

        return {"status": "ok", "speaker_id": speaker_id, "new_name": new_name}

    @app.post("/api/video/{video_id}/suggest-names")
    async def suggest_names(video_id: str):
        """Use Ollama to suggest speaker names from transcript."""
        json_file = output_path / f"{video_id}_labeled.json"
        if not json_file.exists():
            raise HTTPException(404, "Video not found")

        with open(json_file) as f:
            data = json.load(f)

        # Gather intro text from first few segments
        segments = data.get("segments", [])
        intro_text = " ".join(seg.get("text", "") for seg in segments[:30])

        try:
            from .llm import get_llm_client

            client = get_llm_client()
            if not client.is_available():
                return {"suggestions": [], "error": "LLM provider is not available"}

            suggestions = client.extract_names(intro_text)
            return {"suggestions": suggestions}
        except Exception as e:
            logger.error(f"Ollama suggestion error: {e}")
            return {"suggestions": [], "error": str(e)}

    @app.post("/api/video/{video_id}/export")
    async def export_video(video_id: str, request: Request):
        """Export SRT/JSON/annotated video."""
        body = await request.json()
        format_type = body.get("format", "srt")

        file_map = {
            "srt": output_path / f"{video_id}_labeled.srt",
            "json": output_path / f"{video_id}_labeled.json",
            "video": output_path / f"{video_id}_annotated.mp4",
        }

        file_path = file_map.get(format_type)
        if not file_path or not file_path.exists():
            raise HTTPException(404, f"Export file not found: {format_type}")

        return FileResponse(
            path=str(file_path),
            filename=file_path.name,
            media_type="application/octet-stream",
        )

    @app.get("/api/video/{video_id}/annotated")
    async def get_annotated_video(video_id: str):
        """Serve annotated video file."""
        video_file = output_path / f"{video_id}_annotated.mp4"
        if not video_file.exists():
            raise HTTPException(404, "Annotated video not found")
        return FileResponse(str(video_file), media_type="video/mp4")

    @app.get("/api/video/{video_id}/original")
    async def get_original_video(video_id: str):
        """Serve original video file."""
        # Check uploads first, then output
        for search_dir in [upload_path, output_path]:
            for f in search_dir.iterdir():
                if f.stem.startswith(video_id) and f.suffix.lower() in {
                    ".mp4",
                    ".mkv",
                    ".avi",
                    ".mov",
                }:
                    return FileResponse(str(f), media_type="video/mp4")
        raise HTTPException(404, "Original video not found")

    # --- Ollama ---
    @app.get("/api/ollama/status")
    async def ollama_status():
        """Check Ollama connectivity."""
        try:
            from .llm import get_llm_client

            client = get_llm_client()
            available = client.is_available()
            return {"available": available}
        except Exception as e:
            return {"available": False, "error": str(e)}

    @app.get("/api/ollama/models")
    async def ollama_models():
        """List available Ollama models."""
        try:
            from .llm import get_llm_client

            client = get_llm_client()
            if not client.is_available():
                return {"models": [], "available": False}
            models = client.list_models()
            return {"models": models, "available": True}
        except Exception as e:
            return {"models": [], "available": False, "error": str(e)}

    # --- System ---
    @app.get("/api/system/info")
    async def system_info():
        """Return GPU and system information."""
        import platform

        info = {
            "platform": platform.system(),
            "platform_version": platform.version(),
            "python_version": platform.python_version(),
            "machine": platform.machine(),
        }
        try:
            import torch

            info["cuda_available"] = torch.cuda.is_available()
            if torch.cuda.is_available():
                info["gpu_name"] = torch.cuda.get_device_name(0)
                info["gpu_memory_gb"] = round(
                    torch.cuda.get_device_properties(0).total_mem / (1024**3), 1
                )
        except ImportError:
            info["cuda_available"] = False
        return info

    # Serve React build in production
    frontend_dist = Path(__file__).parent.parent / "frontend" / "dist"
    if frontend_dist.exists():
        app.mount(
            "/", StaticFiles(directory=str(frontend_dist), html=True), name="frontend"
        )

    return app


def _run_processing(video_id: str, video_path: Path, output_dir: Path, config: dict):
    """Run the processing pipeline in a background thread."""
    try:
        from .pipeline import MeetingProcessor

        def progress_cb(step, percent, message):
            if video_id in _jobs:
                _jobs[video_id]["step"] = step
                _jobs[video_id]["percent"] = percent
                _jobs[video_id]["logs"].append(
                    {
                        "step": step,
                        "percent": percent,
                        "message": message,
                        "level": "info",
                    }
                )

        processor = MeetingProcessor(progress_callback=progress_cb)
        _processors[video_id] = processor

        processor.process(
            video_path=video_path,
            transcript_path=None,
            output_dir=output_dir,
            asr_model=config.get("asr_model", "base"),
            generate_annotated_video=config.get("generate_annotated_video", True),
        )

        _jobs[video_id]["status"] = "complete"
        _jobs[video_id]["step"] = "complete"
        _jobs[video_id]["percent"] = 100

    except Exception as e:
        logger.error(f"Processing failed for {video_id}: {e}", exc_info=True)
        if video_id in _jobs:
            _jobs[video_id]["status"] = "error"
            _jobs[video_id]["error"] = str(e)
    finally:
        _processors.pop(video_id, None)


def _parse_srt(srt_path: Path) -> list:
    """Parse an SRT file into a list of subtitle dicts."""
    subtitles = []
    with open(srt_path, encoding="utf-8") as f:
        lines = f.readlines()

    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if line and line[0].isdigit() and i + 1 < len(lines):
            timing = lines[i + 1].strip()
            if "-->" in timing:
                parts = timing.split(" --> ")
                if len(parts) == 2:
                    start = _srt_time_to_seconds(parts[0])
                    end = _srt_time_to_seconds(parts[1])
                    text_lines = []
                    j = i + 2
                    while j < len(lines) and lines[j].strip():
                        text_lines.append(lines[j].strip())
                        j += 1
                    if text_lines:
                        full_text = " ".join(text_lines)
                        speaker = ""
                        text = full_text
                        if ": " in full_text:
                            parts2 = full_text.split(": ", 1)
                            speaker = parts2[0]
                            text = parts2[1]
                        subtitles.append(
                            {
                                "start": start,
                                "end": end,
                                "text": text,
                                "speaker": speaker,
                                "full_text": full_text,
                            }
                        )
                    i = j
                    continue
        i += 1
    return subtitles


def _srt_time_to_seconds(time_str: str) -> float:
    """Convert SRT time format to seconds."""
    try:
        parts = time_str.replace(",", ".").split(":")
        return int(parts[0]) * 3600 + int(parts[1]) * 60 + float(parts[2])
    except (ValueError, IndexError):
        return 0.0


def _regenerate_srt(data: dict, srt_path: Path):
    """Regenerate SRT file from JSON data."""
    segments = data.get("segments", [])
    lines = []
    for idx, seg in enumerate(segments, 1):
        start = _format_srt_time(seg.get("start", 0))
        end = _format_srt_time(seg.get("end", 0))
        speaker = seg.get("speaker_name", "Unknown")
        text = seg.get("text", "")
        lines.append(str(idx))
        lines.append(f"{start} --> {end}")
        lines.append(f"{speaker}: {text}")
        lines.append("")

    with open(srt_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


def _format_srt_time(seconds: float) -> str:
    """Format seconds to SRT time string."""
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    ms = int((seconds % 1) * 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"
