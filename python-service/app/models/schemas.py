from pydantic import BaseModel
from typing import List, Optional


# ─── Request Models ────────────────────────────────────────────────────────────

class ExtractRequest(BaseModel):
    url: str


class DownloadRequest(BaseModel):
    url: str
    video_itag: str   # e.g. "137"  (1080p video only)
    audio_itag: str   # e.g. "140"  (audio only)
    job_id: str


# ─── Response Models ───────────────────────────────────────────────────────────

class StreamFormat(BaseModel):
    itag: str
    quality: str
    resolution: Optional[str] = None
    ext: str
    filesize_mb: Optional[float] = None
    codec: Optional[str] = None
    type: str   # "video" | "audio" | "combined"


class VideoInfo(BaseModel):
    title: str
    thumbnail: str
    duration_sec: int
    url_type: str          # "video" | "playlist" | "video_in_playlist"
    formats: List[StreamFormat]


class PlaylistEntry(BaseModel):
    index: int
    title: Optional[str]
    url: str
    duration_sec: Optional[int] = None
    video_id: str


class PlaylistInfo(BaseModel):
    url_type: str = "playlist"
    playlist_title: str
    count: int
    videos: List[PlaylistEntry]


class DownloadStatus(BaseModel):
    job_id: str
    status: str            # "queued" | "downloading" | "merging" | "done" | "error"
    message: Optional[str] = None
