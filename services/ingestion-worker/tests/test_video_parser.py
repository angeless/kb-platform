"""Unit tests for video_parser.py — video parsing with FFmpeg + ASR."""

import json
from unittest.mock import MagicMock, patch, mock_open

import pytest

import importlib.util
import os
import sys

# Ensure ffmpeg module exists (may not be installed in CI)
if "ffmpeg" not in sys.modules:
    sys.modules["ffmpeg"] = MagicMock()

# Direct import to avoid __init__.py loading all sibling parsers (which need pymupdf, whisper, etc.)
_spec = importlib.util.spec_from_file_location(
    "video_parser",
    os.path.join(os.path.dirname(__file__), "..", "worker", "parsers", "video_parser.py"),
)
video_parser = importlib.util.module_from_spec(_spec)
sys.modules["video_parser"] = video_parser
_spec.loader.exec_module(video_parser)


class TestCheckFfmpeg:
    """AC-6: FFmpeg availability check."""

    @patch("subprocess.run", side_effect=FileNotFoundError)
    def test_no_ffmpeg_raises_friendly_error(self, mock_run):
        """AC-6: No FFmpeg → RuntimeError with clear message."""
        with pytest.raises(RuntimeError, match="ffmpeg 未安装"):
            video_parser._check_ffmpeg()

    @patch("subprocess.run")
    def test_ffmpeg_available_no_error(self, mock_run):
        """FFmpeg found → no error."""
        mock_run.return_value = MagicMock(returncode=0)
        video_parser._check_ffmpeg()  # Should not raise


class TestProbeMetadata:
    """AC-4: Metadata extraction."""

    @patch("ffmpeg.probe")
    def test_extracts_metadata(self, mock_probe):
        """AC-4: Metadata includes duration, resolution, fps, audio, subtitles."""
        mock_probe.return_value = {
            "format": {"duration": "120.5"},
            "streams": [
                {"codec_type": "video", "width": 1920, "height": 1080, "r_frame_rate": "30/1"},
                {"codec_type": "audio", "codec_name": "aac"},
                {"codec_type": "subtitle", "codec_name": "srt"},
            ],
        }
        meta = video_parser._probe_metadata("/tmp/test.mp4")

        assert meta["duration_s"] == 120.5
        assert meta["width"] == 1920
        assert meta["height"] == 1080
        assert meta["fps"] == 30.0
        assert meta["has_audio"] is True
        assert meta["subtitle_streams"] == 1

    @patch("ffmpeg.probe", side_effect=Exception("probe failed"))
    def test_probe_failure_returns_empty(self, mock_probe):
        """Probe failure → empty dict, no crash."""
        meta = video_parser._probe_metadata("/tmp/bad.mp4")
        assert meta == {}


class TestExtractSubtitles:
    """AC-2: Subtitle extraction."""

    @patch("subprocess.run")
    def test_extracts_subtitle_text(self, mock_run):
        """AC-2: SRT subtitle → clean text without timestamps."""
        srt_output = "1\n00:00:01,000 --> 00:00:03,000\nHello world\n\n2\n00:00:04,000 --> 00:00:06,000\nSecond line\n"
        mock_run.return_value = MagicMock(returncode=0, stdout=srt_output)

        text = video_parser._extract_subtitles("/tmp/test.mp4", 0)
        assert "Hello world" in text
        assert "Second line" in text
        assert "-->" not in text  # Timestamps stripped

    @patch("subprocess.run")
    def test_no_subtitles_returns_empty(self, mock_run):
        """AC-3: No subtitle content → empty string."""
        mock_run.return_value = MagicMock(returncode=1, stdout="")
        text = video_parser._extract_subtitles("/tmp/test.mp4", 0)
        assert text == ""


def _make_tmp_mock():
    """Create a properly mocked NamedTemporaryFile context manager."""
    mock_file = MagicMock()
    mock_file.name = "/tmp/test_video.mp4"
    mock_file.write = MagicMock()
    mock_cm = MagicMock()
    mock_cm.__enter__ = MagicMock(return_value=mock_file)
    mock_cm.__exit__ = MagicMock(return_value=False)
    return mock_cm


class TestParse:
    """Integration: full parse flow with mocks."""

    @patch("subprocess.run")
    @patch("ffmpeg.probe")
    def test_video_with_audio_calls_asr(self, mock_probe, mock_run_ffmpeg):
        """AC-1: Video with audio → extracts audio → ASR chunks."""
        mock_run_ffmpeg.return_value = MagicMock(returncode=0)
        mock_probe.return_value = {
            "format": {"duration": "60.0"},
            "streams": [
                {"codec_type": "video", "width": 1280, "height": 720, "r_frame_rate": "24/1"},
                {"codec_type": "audio"},
            ],
        }

        mock_asr_chunks = [
            {"content_text": "Hello from video", "page_or_timestamp": "00:00:00-00:00:05", "tags": {"source_type": "audio"}},
        ]

        # Create a mock asr_parser module
        mock_asr = MagicMock()
        mock_asr.parse = MagicMock(return_value=mock_asr_chunks)

        with patch.object(video_parser, "_extract_audio", return_value=True):
            with patch.object(video_parser, "_extract_keyframes", return_value=[]):
                with patch.object(video_parser, "_check_ffmpeg"):
                    with patch.object(video_parser, "_probe_metadata", return_value=mock_probe.return_value |
                                      {"duration_s": 60.0, "has_audio": True, "subtitle_streams": 0,
                                       "width": 1280, "height": 720, "fps": 24.0}):
                        with patch.dict("sys.modules", {"worker.parsers.asr_parser": mock_asr, "worker.parsers": MagicMock(asr_parser=mock_asr)}):
                            with patch("tempfile.NamedTemporaryFile", return_value=_make_tmp_mock()):
                                with patch("builtins.open", mock_open(read_data=b"fake_wav")):
                                    with patch("os.unlink"):
                                        chunks = video_parser.parse(b"fake_video", "test.mp4")

        assert len(chunks) >= 1
        assert chunks[0]["content_text"] == "Hello from video"
        assert chunks[0]["tags"]["source"] == "video_audio"

    @patch("subprocess.run", side_effect=FileNotFoundError)
    def test_no_ffmpeg_raises(self, mock_run):
        """AC-6: parse() raises RuntimeError when FFmpeg missing."""
        with pytest.raises(RuntimeError, match="ffmpeg 未安装"):
            video_parser.parse(b"fake", "test.mp4")

    @patch("subprocess.run")
    @patch("ffmpeg.probe")
    def test_subtitle_stream_creates_chunk(self, mock_probe, mock_run):
        """AC-2: Subtitle stream → independent chunk with source=subtitle."""
        mock_run.return_value = MagicMock(returncode=0)

        with patch.object(video_parser, "_check_ffmpeg"):
            with patch.object(video_parser, "_probe_metadata", return_value={
                "duration_s": 30.0, "has_audio": False, "subtitle_streams": 1,
                "width": 640, "height": 480, "fps": 25.0,
            }):
                with patch.object(video_parser, "_extract_subtitles", return_value="Subtitle text here"):
                    with patch.object(video_parser, "_extract_keyframes", return_value=[]):
                        with patch("tempfile.NamedTemporaryFile", return_value=_make_tmp_mock()):
                            with patch("os.unlink"):
                                chunks = video_parser.parse(b"fake", "test.mp4")

        subtitle_chunks = [c for c in chunks if c.get("tags", {}).get("source") == "subtitle"]
        assert len(subtitle_chunks) == 1
        assert subtitle_chunks[0]["content_text"] == "Subtitle text here"

    @patch("subprocess.run")
    @patch("ffmpeg.probe")
    def test_metadata_in_chunk_tags(self, mock_probe, mock_run):
        """AC-4: Video metadata recorded in chunk tags."""
        mock_run.return_value = MagicMock(returncode=0)

        with patch.object(video_parser, "_check_ffmpeg"):
            with patch.object(video_parser, "_probe_metadata", return_value={
                "duration_s": 90.0, "has_audio": False, "subtitle_streams": 0,
                "width": 1920, "height": 1080, "fps": 30.0,
            }):
                with patch.object(video_parser, "_extract_keyframes", return_value=[]):
                    with patch("tempfile.NamedTemporaryFile", return_value=_make_tmp_mock()):
                        with patch("os.unlink"):
                            chunks = video_parser.parse(b"fake", "test.mp4")

        assert len(chunks) >= 1
        tags = chunks[0]["tags"]
        assert tags["duration_s"] == 90.0
        assert tags["resolution"] == "1920x1080"

    @patch("subprocess.run")
    @patch("ffmpeg.probe")
    def test_keyframe_ocr_creates_chunks(self, mock_probe, mock_run):
        """v0.48.4 AC: Keyframes with OCR text → chunks with source=video_frame."""
        mock_run.return_value = MagicMock(returncode=0)

        fake_frames = [("/tmp/frames/frame_0001.jpg", 0.0), ("/tmp/frames/frame_0002.jpg", 30.0)]
        mock_ocr_chunks = [
            {"content_text": "Slide title", "page_or_timestamp": "page_1", "tags": {}},
        ]
        mock_ocr = MagicMock()
        mock_ocr.parse = MagicMock(return_value=mock_ocr_chunks)

        with patch.object(video_parser, "_check_ffmpeg"):
            with patch.object(video_parser, "_probe_metadata", return_value={
                "duration_s": 60.0, "has_audio": False, "subtitle_streams": 0,
                "width": 1920, "height": 1080, "fps": 30.0,
            }):
                with patch.object(video_parser, "_extract_keyframes", return_value=fake_frames):
                    with patch.object(video_parser, "_ocr_frames", return_value=[{
                        "content_text": "Slide title",
                        "page_or_timestamp": "frame_0s",
                        "tags": {"source": "video_frame", "timestamp_s": 0.0, "video_filename": "test.mp4"},
                    }]):
                        with patch("tempfile.NamedTemporaryFile", return_value=_make_tmp_mock()):
                            with patch("os.unlink"):
                                with patch("shutil.rmtree"):
                                    chunks = video_parser.parse(b"fake", "test.mp4")

        frame_chunks = [c for c in chunks if c.get("tags", {}).get("source") == "video_frame"]
        assert len(frame_chunks) >= 1
        assert frame_chunks[0]["content_text"] == "Slide title"
        assert frame_chunks[0]["tags"]["timestamp_s"] == 0.0

    def test_extract_keyframes_failure_returns_empty(self):
        """Keyframe extraction failure → empty list, no crash."""
        with patch("ffmpeg.input", side_effect=Exception("ffmpeg error")):
            frames = video_parser._extract_keyframes("/tmp/nonexistent.mp4")
        assert frames == []
