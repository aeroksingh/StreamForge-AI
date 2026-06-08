import yt_dlp
from app.models.schemas import StreamFormat, VideoInfo, PlaylistInfo, PlaylistEntry


def detect_url_type(url: str) -> str:
    if "playlist?list=" in url:
        return "playlist"
    elif "watch?v=" in url and "list=" in url:
        return "video_in_playlist"
    else:
        return "video"


def extract_video_info(url: str) -> VideoInfo:
    ydl_opts = {"quiet": True, "no_warnings": True}
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)

    formats = []
    for f in info.get("formats", []):
        vcodec = f.get("vcodec", "none")
        acodec = f.get("acodec", "none")
        if vcodec == "none" and acodec == "none":
            continue
        if vcodec != "none" and acodec != "none":
            stream_type = "combined"
        elif vcodec != "none":
            stream_type = "video"
        else:
            stream_type = "audio"
        filesize = f.get("filesize") or f.get("filesize_approx")
        filesize_mb = round(filesize / 1_000_000, 2) if filesize else None
        formats.append(StreamFormat(
            itag=str(f["format_id"]),
            quality=f.get("format_note", ""),
            resolution=f.get("resolution"),
            ext=f.get("ext", ""),
            filesize_mb=filesize_mb,
            codec=vcodec if stream_type != "audio" else acodec,
            type=stream_type,
        ))

    return VideoInfo(
        title=info.get("title", ""),
        thumbnail=info.get("thumbnail", ""),
        duration_sec=info.get("duration", 0),
        url_type=detect_url_type(url),
        formats=formats,
    )


def extract_playlist_info(url: str) -> PlaylistInfo:
    ydl_opts = {"quiet": True, "no_warnings": True, "extract_flat": True}
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)
    entries = info.get("entries", [])
    videos = []
    for i, entry in enumerate(entries):
        if not entry:
            continue
        video_id = entry.get("id", "")
        videos.append(PlaylistEntry(
            index=i + 1,
            title=entry.get("title"),
            url=f"https://www.youtube.com/watch?v={video_id}",
            duration_sec=entry.get("duration"),
            video_id=video_id,
        ))
    return PlaylistInfo(
        playlist_title=info.get("title", "Unknown Playlist"),
        count=len(videos),
        videos=videos,
    )


def make_progress_hook(job_id: str, stream_label: str):
    """
    yt-dlp calls this function on every progress update.
    We store percent + eta in Redis so the extension can read it.
    """
    from app.services.redis_service import set_status

    def hook(d):
        if d["status"] == "downloading":
            percent  = d.get("_percent_str", "0%").strip()
            speed    = d.get("_speed_str", "").strip()
            eta      = d.get("_eta_str", "").strip()
            msg = f"{stream_label}: {percent} at {speed} — ETA {eta}"
            set_status(job_id, "downloading", msg)

        elif d["status"] == "finished":
            set_status(job_id, "downloading", f"{stream_label}: processing...")

    return hook


def download_stream(url: str, itag: str, output_path: str, job_id: str = "", label: str = ""):
    hooks = [make_progress_hook(job_id, label)] if job_id else []
    ydl_opts = {
        "format": itag,
        "outtmpl": output_path,
        "quiet": True,
        "no_warnings": True,
        "progress_hooks": hooks,
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])