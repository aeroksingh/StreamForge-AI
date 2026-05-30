import os
import shutil
from dotenv import load_dotenv

load_dotenv()

TEMP_DIR     = os.getenv("TEMP_DIR", "temp")
DOWNLOAD_DIR = os.getenv("DOWNLOAD_DIR", "downloads")


# ─── Path Builders ─────────────────────────────────────────────────────────────

def video_temp_path(job_id: str) -> str:
    """Path where the raw video-only stream is saved before merge."""
    return os.path.join(TEMP_DIR, f"{job_id}_video.mp4")


def audio_temp_path(job_id: str) -> str:
    """Path where the raw audio-only stream is saved before merge."""
    return os.path.join(TEMP_DIR, f"{job_id}_audio.mp4")


def final_output_path(job_id: str) -> str:
    """Path of the final merged mp4 file served to the user."""
    return os.path.join(DOWNLOAD_DIR, f"{job_id}_final.mp4")


def playlist_zip_path(job_id: str) -> str:
    """Path of the zip archive for playlist downloads."""
    return os.path.join(DOWNLOAD_DIR, f"{job_id}_playlist.zip")


# ─── Directory Setup ───────────────────────────────────────────────────────────

def ensure_dirs():
    """
    Makes sure temp/ and downloads/ folders exist.
    Call this once at app startup so nothing crashes on first run.
    """
    os.makedirs(TEMP_DIR, exist_ok=True)
    os.makedirs(DOWNLOAD_DIR, exist_ok=True)


# ─── Cleanup ──────────────────────────────────────────────────────────────────

def delete_file(path: str):
    """Deletes a single file if it exists. Silent if already gone."""
    try:
        if os.path.exists(path):
            os.remove(path)
            print(f"[cleanup] deleted {path}")
    except Exception as e:
        print(f"[cleanup] could not delete {path}: {e}")


def cleanup_job_temp(job_id: str):
    """
    Removes the two temp files (video + audio) for a job.
    Called automatically by ffmpeg_service after merge,
    but also useful to call manually if a job errors mid-way.
    """
    delete_file(video_temp_path(job_id))
    delete_file(audio_temp_path(job_id))


def cleanup_final(job_id: str):
    """
    Removes the final merged file.
    Call this after the user has downloaded the file
    so you don't fill up disk space.
    """
    delete_file(final_output_path(job_id))


def cleanup_all_temp():
    """
    Wipes the entire temp/ folder.
    Useful on server startup to clear any files
    left behind from a previous crashed session.
    """
    if os.path.exists(TEMP_DIR):
        shutil.rmtree(TEMP_DIR)
        os.makedirs(TEMP_DIR)
        print(f"[cleanup] temp/ folder wiped and recreated")


# ─── File Info ────────────────────────────────────────────────────────────────

def file_size_mb(path: str) -> float:
    """Returns file size in MB, rounded to 2 decimal places."""
    if not os.path.exists(path):
        return 0.0
    return round(os.path.getsize(path) / 1_000_000, 2)


def file_exists(path: str) -> bool:
    return os.path.exists(path) and os.path.getsize(path) > 0
