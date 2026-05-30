import yt_dlp
from app.models.schemas import StreamFormat, VideoInfo, PlaylistInfo, PlaylistEntry


# ─── URL Type Detection ────────────────────────────────────────────────────────

def detect_url_type(url: str) -> str:
    """
    Figures out what kind of YouTube URL was pasted.
    Three possible cases:
      - plain video:          youtube.com/watch?v=xxx
      - video inside playlist: youtube.com/watch?v=xxx&list=PLxxx
      - full playlist:        youtube.com/playlist?list=PLxxx
    """
    if "playlist?list=" in url:
        return "playlist"
    elif "watch?v=" in url and "list=" in url:
        return "video_in_playlist"
    else:
        return "video"


# ─── Single Video Extract ──────────────────────────────────────────────────────

def extract_video_info(url: str) -> VideoInfo:
    """
    Calls yt-dlp to get all available formats for a single video.
    download=False means we are only fetching metadata, not downloading.
    """
    ydl_opts = {
        "quiet": True,
        "no_warnings": True,
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)

    formats = []
    for f in info.get("formats", []):
        vcodec = f.get("vcodec", "none")
        acodec = f.get("acodec", "none")

        # skip formats that have neither
        if vcodec == "none" and acodec == "none":
            continue

        # determine stream type
        if vcodec != "none" and acodec != "none":
            stream_type = "combined"
        elif vcodec != "none":
            stream_type = "video"
        else:
            stream_type = "audio"

        # file size — yt-dlp gives exact or approx
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

    url_type = detect_url_type(url)

    return VideoInfo(
        title=info.get("title", ""),
        thumbnail=info.get("thumbnail", ""),
        duration_sec=info.get("duration", 0),
        url_type=url_type,
        formats=formats,
    )


# ─── Playlist Extract ─────────────────────────────────────────────────────────

def extract_playlist_info(url: str) -> PlaylistInfo:
    """
    Fetches only the playlist index — titles, ids, durations.
    extract_flat=True is critical: without it yt-dlp visits every
    single video page which takes minutes for large playlists.
    """
    ydl_opts = {
        "quiet": True,
        "no_warnings": True,
        "extract_flat": True,   # only index metadata, no per-video fetch
    }

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


# ─── Download a Single Stream ──────────────────────────────────────────────────

def download_stream(url: str, itag: str, output_path: str):
    """
    Downloads one stream (video-only or audio-only) to output_path.
    The file will have no extension added — we control the exact path.
    """
    ydl_opts = {
        "format": itag,
        "outtmpl": output_path,
        "quiet": False,       # set True in production, False so you can see progress
        "no_warnings": True,
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])
