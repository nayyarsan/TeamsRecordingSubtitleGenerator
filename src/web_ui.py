from flask import Flask, jsonify, send_file
from pathlib import Path
import json

from .utils import get_logger

logger = get_logger(__name__)


class WebUI:
    """Flask web application for video viewer."""

    def __init__(self, output_dir: Path):
        """
        Initialize web UI.

        Args:
            output_dir: Directory containing processed videos and metadata
        """
        self.output_dir = Path(output_dir)
        self.app = Flask(__name__, template_folder=None)
        self.app.config["JSON_SORT_KEYS"] = False

        # Register routes
        self._register_routes()

        logger.info(f"WebUI initialized with output dir: {output_dir}")

    def _register_routes(self):
        """Register Flask routes."""

        @self.app.route("/")
        def index():
            return self._render_index()

        @self.app.route("/api/videos")
        def list_videos():
            return self._list_videos()

        @self.app.route("/api/video/<video_id>/metadata")
        def get_metadata(video_id):
            return self._get_metadata(video_id)

        @self.app.route("/api/video/<video_id>/subtitles")
        def get_subtitles(video_id):
            return self._get_subtitles(video_id)

        @self.app.route("/video/<video_id>/annotated")
        def get_annotated_video(video_id):
            return self._get_annotated_video(video_id)

        @self.app.route("/api/video/<video_id>/original")
        def get_original_video(video_id):
            return self._get_original_video(video_id)

    def _render_index(self):
        """Render main HTML page."""
        html = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Speaker Labeling - Video Viewer</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }
        
        .container {
            max-width: 1200px;
            margin: 0 auto;
        }
        
        .header {
            background: white;
            padding: 30px;
            border-radius: 10px;
            margin-bottom: 30px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        }
        
        .header h1 {
            color: #333;
            margin-bottom: 10px;
            font-size: 32px;
        }
        
        .header p {
            color: #666;
            font-size: 14px;
        }
        
        .main-grid {
            display: grid;
            grid-template-columns: 300px 1fr;
            gap: 30px;
            margin-bottom: 30px;
        }
        
        .video-list {
            background: white;
            border-radius: 10px;
            padding: 20px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
            height: fit-content;
            max-height: 600px;
            overflow-y: auto;
        }
        
        .video-list h2 {
            font-size: 18px;
            margin-bottom: 15px;
            color: #333;
        }
        
        .video-item {
            padding: 12px;
            margin-bottom: 8px;
            background: #f5f5f5;
            border-left: 4px solid #667eea;
            border-radius: 4px;
            cursor: pointer;
            transition: all 0.2s;
            font-size: 13px;
            color: #555;
        }
        
        .video-item:hover {
            background: #e8e8e8;
            transform: translateX(4px);
        }
        
        .video-item.active {
            background: #667eea;
            color: white;
        }
        
        .video-name {
            font-weight: 600;
            margin-bottom: 4px;
        }
        
        .video-time {
            font-size: 11px;
            opacity: 0.7;
        }
        
        .viewer {
            background: white;
            border-radius: 10px;
            padding: 20px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        }
        
        .viewer-title {
            font-size: 20px;
            font-weight: 600;
            margin-bottom: 15px;
            color: #333;
        }
        
        .video-player {
            background: #000;
            border-radius: 8px;
            margin-bottom: 15px;
            overflow: hidden;
            aspect-ratio: 16 / 9;
        }
        
        video {
            width: 100%;
            height: 100%;
            display: block;
            object-fit: cover;
        }
        
        .transcript-section {
            background: #f9f9f9;
            border: 1px solid #e0e0e0;
            border-radius: 6px;
            overflow: hidden;
            margin-bottom: 20px;
        }
        
        .transcript-header {
            padding: 12px 15px;
            border-bottom: 1px solid #e0e0e0;
            font-size: 12px;
            text-transform: uppercase;
            color: #999;
            font-weight: 600;
            background: #fff;
        }
        
        .transcript-list {
            max-height: 300px;
            overflow-y: auto;
            padding: 0;
        }
        
        .transcript-item {
            padding: 12px 15px;
            border-bottom: 1px solid #f0f0f0;
            cursor: pointer;
            transition: all 0.2s;
            font-size: 13px;
            line-height: 1.5;
            color: #555;
            background: #fff;
        }
        
        .transcript-item:hover {
            background: #f5f5f5;
        }
        
        .transcript-item.active {
            background: #e8f0ff;
            border-left: 4px solid #667eea;
            padding-left: 11px;
        }
        
        .transcript-item-time {
            font-size: 11px;
            color: #999;
            margin-bottom: 4px;
        }
        
        .transcript-item-speaker {
            font-weight: 600;
            color: #667eea;
            margin-bottom: 4px;
        }
        
        .transcript-item-text {
            color: #333;
        }
        
        .metadata-section {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 20px;
            margin-top: 20px;
        }
        
        .metadata-card {
            background: #f5f5f5;
            padding: 15px;
            border-radius: 6px;
        }
        
        .metadata-card h3 {
            font-size: 12px;
            text-transform: uppercase;
            color: #999;
            margin-bottom: 10px;
            font-weight: 600;
        }
        
        .metadata-value {
            font-size: 16px;
            color: #333;
            font-weight: 500;
        }
        
        .speaker-list {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(150px, 1fr));
            gap: 10px;
            margin-top: 20px;
        }
        
        .speaker-badge {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 10px;
            border-radius: 6px;
            text-align: center;
            font-size: 13px;
            font-weight: 500;
        }
        
        .loading {
            text-align: center;
            padding: 40px;
            color: #999;
        }
        
        .error {
            background: #fee;
            color: #c33;
            padding: 15px;
            border-radius: 6px;
            margin-bottom: 20px;
            border-left: 4px solid #c33;
        }
        
        .download-section {
            display: flex;
            gap: 10px;
            margin-top: 20px;
        }
        
        .btn {
            padding: 10px 20px;
            background: #667eea;
            color: white;
            border: none;
            border-radius: 6px;
            cursor: pointer;
            font-size: 13px;
            font-weight: 600;
            transition: all 0.2s;
        }
        
        .btn:hover {
            background: #764ba2;
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4);
        }
        
        .btn.secondary {
            background: #f0f0f0;
            color: #333;
        }
        
        .btn.secondary:hover {
            background: #e0e0e0;
        }
        
        .tabs {
            display: flex;
            gap: 10px;
            margin-bottom: 20px;
            border-bottom: 1px solid #e0e0e0;
        }
        
        .tab {
            padding: 12px 16px;
            background: none;
            border: none;
            border-bottom: 3px solid transparent;
            cursor: pointer;
            font-size: 14px;
            font-weight: 500;
            color: #999;
            transition: all 0.2s;
        }
        
        .tab.active {
            color: #667eea;
            border-bottom-color: #667eea;
        }
        
        .tab-content {
            display: none;
        }
        
        .tab-content.active {
            display: block;
        }
        
        @media (max-width: 768px) {
            .main-grid {
                grid-template-columns: 1fr;
            }
            
            .metadata-section {
                grid-template-columns: 1fr;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🎬 Speaker Labeling Viewer</h1>
            <p>View videos with face detection and speaker-labeled subtitles</p>
        </div>
        
        <div class="main-grid">
            <!-- Video List -->
            <div class="video-list">
                <h2>Videos</h2>
                <div id="videoList" style="min-height: 100px;">
                    <div class="loading">Loading videos...</div>
                </div>
            </div>
            
            <!-- Viewer -->
            <div class="viewer">
                <div class="viewer-title" id="viewerTitle">Select a video to view</div>
                
                <div id="errorContainer"></div>
                
                <!-- Tabs -->
                <div class="tabs">
                    <button class="tab active" onclick="switchTab('player')">Video Player</button>
                    <button class="tab" onclick="switchTab('metadata')">Metadata</button>
                </div>
                
                <!-- Player Tab -->
                <div id="playerTab" class="tab-content active">
                    <div class="video-player">
                        <video id="videoPlayer" controls>
                            <source src="" type="video/mp4">
                            Your browser does not support HTML5 video.
                        </video>
                    </div>
                    
                    <div class="transcript-section">
                        <div class="transcript-header">Transcript Timeline</div>
                        <div class="transcript-list" id="transcriptList">
                            <div style="padding: 20px; text-align: center; color: #999;">Loading transcript...</div>
                        </div>
                    </div>
                </div>
                
                <!-- Metadata Tab -->
                <div id="metadataTab" class="tab-content">
                    <div id="metadataContainer" class="loading">Loading metadata...</div>
                </div>
            </div>
        </div>
    </div>
    
    <script>
        let currentVideo = null;
        let allSubtitles = [];
        
        async function loadVideos() {
            try {
                const response = await fetch('/api/videos');
                const data = await response.json();
                
                const listDiv = document.getElementById('videoList');
                if (data.videos.length === 0) {
                    listDiv.innerHTML = '<div style="color: #999; text-align: center; padding: 20px;">No videos found</div>';
                    return;
                }
                
                listDiv.innerHTML = data.videos.map(video => `
                    <div class="video-item" data-video-id="${video.id}" onclick="selectVideo('${video.id}')">
                        <div class="video-name">${escapeHtml(video.name)}</div>
                        <div class="video-time">${formatDate(video.timestamp)}</div>
                    </div>
                `).join('');
                
                // Select first video by default
                if (data.videos.length > 0) {
                    selectVideo(data.videos[0].id);
                }
            } catch (error) {
                console.error('Error loading videos:', error);
                document.getElementById('videoList').innerHTML = '<div style="color: #c33;">Error loading videos</div>';
            }
        }
        
        async function selectVideo(videoId) {
            currentVideo = videoId;
            
            // Update active state
            document.querySelectorAll('.video-item').forEach(el => el.classList.remove('active'));
            const activeItem = event?.target?.closest('.video-item') || document.querySelector(`[data-video-id="${videoId}"]`);
            if (activeItem) {
                activeItem.classList.add('active');
            }
            
            // Update player
            document.getElementById('videoPlayer').src = `/video/${videoId}/annotated`;
            document.getElementById('viewerTitle').textContent = `Playing: ${videoId}`;
            
            // Load subtitles
            await loadSubtitles(videoId);
            
            // Load metadata
            await loadMetadata(videoId);
            
            // Clear error
            document.getElementById('errorContainer').innerHTML = '';
        }
        
        async function loadSubtitles(videoId) {
            try {
                const response = await fetch(`/api/video/${videoId}/subtitles`);
                const data = await response.json();
                allSubtitles = data.subtitles;
                
                // Render transcript list
                renderTranscript();
                
                // Sync subtitles with video
                const video = document.getElementById('videoPlayer');
                video.ontimeupdate = () => updateTranscriptHighlight(video.currentTime);
            } catch (error) {
                console.error('Error loading subtitles:', error);
            }
        }
        
        function renderTranscript() {
            const listDiv = document.getElementById('transcriptList');
            
            if (allSubtitles.length === 0) {
                listDiv.innerHTML = '<div style="padding: 20px; text-align: center; color: #999;">No transcript available</div>';
                return;
            }
            
            listDiv.innerHTML = allSubtitles.map((subtitle, idx) => {
                const speakerMatch = subtitle.text.match(/^([^:]+):\\s*(.*)/);
                const speaker = speakerMatch ? speakerMatch[1] : '';
                const text = speakerMatch ? speakerMatch[2] : subtitle.text;
                
                return `
                    <div class="transcript-item" id="subtitle-${idx}" onclick="seekToSubtitle(${subtitle.start})">
                        <div class="transcript-item-time">${formatTime(subtitle.start)} - ${formatTime(subtitle.end)}</div>
                        ${speaker ? `<div class="transcript-item-speaker">${escapeHtml(speaker)}</div>` : ''}
                        <div class="transcript-item-text">${escapeHtml(text)}</div>
                    </div>
                `;
            }).join('');
        }
        
        function updateTranscriptHighlight(currentTime) {
            // Remove previous active highlight
            document.querySelectorAll('.transcript-item.active').forEach(el => el.classList.remove('active'));
            
            // Find and highlight current subtitle
            const currentSubtitle = allSubtitles.findIndex(s => s.start <= currentTime && currentTime < s.end);
            
            if (currentSubtitle >= 0) {
                const element = document.getElementById(`subtitle-${currentSubtitle}`);
                if (element) {
                    element.classList.add('active');
                    // Scroll to active item
                    element.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
                }
            }
        }
        
        function seekToSubtitle(time) {
            const video = document.getElementById('videoPlayer');
            video.currentTime = time;
        }
        
        function formatTime(seconds) {
            const mins = Math.floor(seconds / 60);
            const secs = Math.floor(seconds % 60);
            return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
        }
        
        async function loadMetadata(videoId) {
            try {
                const response = await fetch(`/api/video/${videoId}/metadata`);
                const data = await response.json();
                
                const container = document.getElementById('metadataContainer');
                
                let html = `
                    <div class="metadata-section">
                        <div class="metadata-card">
                            <h3>Duration</h3>
                            <div class="metadata-value">${data.duration}</div>
                        </div>
                        <div class="metadata-card">
                            <h3>Speakers Detected</h3>
                            <div class="metadata-value">${data.speaker_count}</div>
                        </div>
                        <div class="metadata-card">
                            <h3>Resolution</h3>
                            <div class="metadata-value">${data.resolution}</div>
                        </div>
                        <div class="metadata-card">
                            <h3>Segments</h3>
                            <div class="metadata-value">${data.segment_count}</div>
                        </div>
                    </div>
                `;
                
                if (data.speakers && data.speakers.length > 0) {
                    html += '<h3 style="margin-top: 20px; font-size: 14px;">Speakers:</h3>';
                    html += '<div class="speaker-list">';
                    data.speakers.forEach(speaker => {
                        html += `
                            <div class="speaker-badge">
                                ${escapeHtml(speaker)}
                            </div>
                        `;
                    });
                    html += '</div>';
                }
                
                container.innerHTML = html;
            } catch (error) {
                console.error('Error loading metadata:', error);
                document.getElementById('metadataContainer').innerHTML = '<div style="color: #c33;">Error loading metadata</div>';
            }
        }
        
        function switchTab(tabName) {
            // Update buttons
            document.querySelectorAll('.tab').forEach(el => el.classList.remove('active'));
            event.target.classList.add('active');
            
            // Update content
            document.querySelectorAll('.tab-content').forEach(el => el.classList.remove('active'));
            document.getElementById(tabName + 'Tab').classList.add('active');
        }
        
        function formatDate(timestamp) {
            const date = new Date(timestamp * 1000);
            return date.toLocaleString();
        }
        
        function escapeHtml(text) {
            const div = document.createElement('div');
            div.textContent = text;
            return div.innerHTML;
        }
        
        // Load videos on page load
        loadVideos();
    </script>
</body>
</html>
        """
        return html

    def _list_videos(self):
        """List all processed videos."""
        videos = []

        if self.output_dir.exists():
            for json_file in self.output_dir.glob("*_labeled.json"):
                base_name = json_file.stem.replace("_labeled", "")
                stat = json_file.stat()

                videos.append(
                    {"id": base_name, "name": base_name, "timestamp": stat.st_mtime}
                )

        return jsonify(
            {"videos": sorted(videos, key=lambda x: x["timestamp"], reverse=True)}
        )

    def _get_metadata(self, video_id):
        """Get metadata for a video."""
        json_file = self.output_dir / f"{video_id}_labeled.json"

        if not json_file.exists():
            return jsonify({"error": "Video not found"}), 404

        try:
            with open(json_file) as f:
                data = json.load(f)

            speakers = list(
                set(seg.get("speaker", "Unknown") for seg in data.get("segments", []))
            )

            return jsonify(
                {
                    "duration": data.get("duration", "Unknown"),
                    "speaker_count": len(speakers),
                    "speakers": speakers,
                    "segment_count": len(data.get("segments", [])),
                    "resolution": data.get("video_resolution", "Unknown"),
                    "fps": data.get("fps", "Unknown"),
                }
            )
        except Exception as e:
            logger.error(f"Error reading metadata: {e}")
            return jsonify({"error": str(e)}), 500

    def _get_subtitles(self, video_id):
        """Get subtitles for a video in JSON format."""
        srt_file = self.output_dir / f"{video_id}_labeled.srt"

        if not srt_file.exists():
            return jsonify({"subtitles": []})

        try:
            subtitles = []
            with open(srt_file) as f:
                lines = f.readlines()

            i = 0
            while i < len(lines):
                line = lines[i].strip()

                if line and line[0].isdigit():
                    # Found subtitle number, next line should be timing
                    if i + 1 < len(lines):
                        timing = lines[i + 1].strip()
                        if "-->" in timing:
                            parts = timing.split(" --> ")
                            if len(parts) == 2:
                                start = self._srt_time_to_seconds(parts[0])
                                end = self._srt_time_to_seconds(parts[1])

                                # Get text
                                text_lines = []
                                j = i + 2
                                while j < len(lines) and lines[j].strip():
                                    text_lines.append(lines[j].strip())
                                    j += 1

                                if text_lines:
                                    subtitles.append(
                                        {
                                            "start": start,
                                            "end": end,
                                            "text": " ".join(text_lines),
                                        }
                                    )

                                i = j
                                continue

                i += 1

            return jsonify({"subtitles": subtitles})

        except Exception as e:
            logger.error(f"Error reading subtitles: {e}")
            return jsonify({"subtitles": []})

    def _srt_time_to_seconds(self, time_str: str) -> float:
        """Convert SRT time format to seconds."""
        try:
            parts = time_str.replace(",", ".").split(":")
            hours = int(parts[0])
            minutes = int(parts[1])
            seconds = float(parts[2])
            return hours * 3600 + minutes * 60 + seconds
        except (ValueError, IndexError):
            return 0.0

    def _get_annotated_video(self, video_id):
        """Serve annotated video."""
        video_file = self.output_dir / f"{video_id}_annotated.mp4"

        if not video_file.exists():
            return "Video not found", 404

        return send_file(str(video_file), mimetype="video/mp4", as_attachment=False)

    def _get_original_video(self, video_id):
        """Serve original video."""
        video_file = self.output_dir / f"{video_id}.mp4"

        if not video_file.exists():
            return "Video not found", 404

        return send_file(str(video_file), mimetype="video/mp4", as_attachment=False)

    def run(self, host: str = "0.0.0.0", port: int = 5000, debug: bool = False):
        """Run the Flask app."""
        logger.info(f"Starting web UI on {host}:{port}")
        self.app.run(host=host, port=port, debug=debug, use_reloader=False)
