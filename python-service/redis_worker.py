"""
redis_worker.py
---------------
Standalone worker — Spring Boot se jobs pull karta hai Redis queue se,
download karta hai, merge karta hai, aur progress Redis mein save karta hai.

Run: python3 redis_worker.py
"""

import redis
import json
import os
import time
import subprocess
import logging
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s %(message)s",
    datefmt="%H:%M:%S"
)
log = logging.getLogger(__name__)

REDIS_URL    = os.getenv("REDIS_URL", "redis://localhost:6379")
QUEUE_NAME   = "download_queue"
TEMP_DIR     = os.getenv("TEMP_DIR", "temp")
DOWNLOAD_DIR = os.getenv("DOWNLOAD_DIR", "downloads")

client = redis.from_url(REDIS_URL, decode_responses=True)

os.makedirs(TEMP_DIR, exist_ok=True)
os.makedirs(DOWNLOAD_DIR, exist_ok=True)


# ── Progress helpers ──────────────────────────────────────────────────────────

def set_progress(job_id: str, status: str, message: str = "",
                 progress: int = 0, extra: dict = None):
    """
    Writes progress to Redis as JSON.
    Spring Boot reads this key: progress:{job_id}
    Also writes to job_status:{job_id} hash for direct polling.
    """
    data = {
        "status":   status,
        "message":  message,
        "progress": progress,
    }
    if extra:
        data.update(extra)

    # For Spring Boot (reads progress:{job_id} as JSON string)
    client.set(f"progress:{job_id}", json.dumps(data), ex=3600)

    # For direct extension polling (reads job_status:{job_id} as hash)
    client.hset(f"job_status:{job_id}", mapping={
        "status":  status,
        "message": message,
    })
    client.expire(f"job_status:{job_id}", 3600)


def make_yt_progress_hook(job_id: str, label: str):
    """yt-dlp calls this on every chunk — we parse and push to Redis."""
    import yt_dlp

    def hook(d):
        if d["status"] == "downloading":
            pct_str   = d.get("_percent_str", "0%").strip()
            speed_str = d.get("_speed_str", "").strip()
            eta_str   = d.get("_eta_str", "").strip()

            # Parse percent number for Spring Boot progress field
            try:
                pct_num = float(pct_str.replace("%", ""))
            except ValueError:
                pct_num = 0

            msg = f"{label}: {pct_str} at {speed_str} — ETA {eta_str}"
            set_progress(job_id, "downloading", msg, int(pct_num))

        elif d["status"] == "finished":
            set_progress(job_id, "downloading", f"{label}: processing...", 90)

    return hook


# ── Download helpers ──────────────────────────────────────────────────────────

def download_stream(url: str, itag: str, output_path: str,
                    job_id: str, label: str):
    import yt_dlp
    ydl_opts = {
        "format":         itag,
        "outtmpl":        output_path,
        "quiet":          True,
        "no_warnings":    True,
        "progress_hooks": [make_yt_progress_hook(job_id, label)],
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])


def merge(video_path: str, audio_path: str, output_path: str):
    cmd = [
        "ffmpeg",
        "-i", video_path,
        "-i", audio_path,
        "-c:v", "copy",
        "-c:a", "copy",
        "-map", "0:v:0",
        "-map", "1:a:0",
        "-y",
        output_path,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"FFmpeg error: {result.stderr}")

    if os.path.exists(video_path): os.remove(video_path)
    if os.path.exists(audio_path): os.remove(audio_path)


def get_video_info(url: str) -> dict:
    """Fetch title + thumbnail without downloading."""
    import yt_dlp
    with yt_dlp.YoutubeDL({"quiet": True, "no_warnings": True}) as ydl:
        info = ydl.extract_info(url, download=False)
    return {
        "title":     info.get("title", ""),
        "thumbnail": info.get("thumbnail", ""),
        "duration":  info.get("duration", 0),
    }


def pick_itags(url: str, quality: str) -> tuple[str, str]:
    """
    If Spring Boot sent quality string instead of itags,
    pick best matching itag automatically.
    """
    import yt_dlp
    quality_map = {
        "2160p": "313", "1440p": "271",
        "1080p": "137", "720p":  "136",
        "480p":  "135", "360p":  "134",
        "240p":  "133", "144p":  "160",
        "best":  "bestvideo[ext=mp4]",
        "worst": "worstvideo[ext=mp4]",
    }
    video_itag = quality_map.get(quality, "137")
    audio_itag = "140"  # AAC always
    return video_itag, audio_itag


# ── Main job processor ────────────────────────────────────────────────────────

def process_job(job: dict):
    job_id    = job.get("job_id", "")
    url       = job.get("url") or job.get("youtube_url", "")
    video_itag = job.get("video_itag", "")
    audio_itag = job.get("audio_itag", "")
    quality   = job.get("quality", "1080p")
    fmt       = job.get("format", "mp4")

    if not job_id or not url:
        log.warning("Invalid job — missing job_id or url: %s", job)
        return

    log.info("Processing job: id=%s url=%s", job_id, url)

    video_path = os.path.join(TEMP_DIR, f"{job_id}_video.mp4")
    audio_path = os.path.join(TEMP_DIR, f"{job_id}_audio.mp4")
    final_path = os.path.join(DOWNLOAD_DIR, f"{job_id}_final.mp4")

    try:
        # If itags not sent by Spring Boot, pick from quality string
        if not video_itag:
            video_itag, audio_itag = pick_itags(url, quality)

        # Fetch title + push to progress
        set_progress(job_id, "extracting", "Fetching video info...", 5)
        try:
            info = get_video_info(url)
            set_progress(job_id, "extracting", "Info fetched", 8,
                         extra={"title": info["title"],
                                "thumbnail": info["thumbnail"]})
        except Exception:
            pass

        # Download video stream
        set_progress(job_id, "downloading", "Starting video download...", 10)
        download_stream(url, video_itag, video_path, job_id, "Video")

        # Download audio stream
        set_progress(job_id, "downloading", "Starting audio download...", 60)
        download_stream(url, audio_itag, audio_path, job_id, "Audio")

        # FFmpeg merge
        set_progress(job_id, "merging", "Merging video + audio...", 90)
        merge(video_path, audio_path, final_path)

        # Done
        file_size = os.path.getsize(final_path) if os.path.exists(final_path) else 0
        set_progress(job_id, "done",
                     f"Ready — {round(file_size/1_000_000, 2)} MB",
                     100,
                     extra={
                         "file_path": final_path,
                         "file_size": file_size,
                     })
        log.info("Job done: %s → %s (%.2f MB)", job_id, final_path, file_size/1_000_000)

    except Exception as e:
        log.error("Job failed: %s → %s", job_id, str(e))
        # cleanup temp files
        if os.path.exists(video_path): os.remove(video_path)
        if os.path.exists(audio_path): os.remove(audio_path)
        set_progress(job_id, "error", str(e), 0)


# ── Worker loop ───────────────────────────────────────────────────────────────

def run_worker():
    log.info("Worker started — listening on queue: %s", QUEUE_NAME)
    log.info("Redis: %s", REDIS_URL)

    while True:
        try:
            # Blocking pop — waits 5s for a job
            result = client.brpop(QUEUE_NAME, timeout=5)
            if result:
                _, raw = result
                job = json.loads(raw)
                log.info("Job received: %s", job.get("job_id"))
                process_job(job)
        except redis.exceptions.ConnectionError:
            log.error("Redis connection lost — retrying in 5s...")
            time.sleep(5)
        except Exception as e:
            log.error("Worker error: %s", str(e))
            time.sleep(1)


if __name__ == "__main__":
    run_worker()