from fastapi import APIRouter, BackgroundTasks, HTTPException
from app.models.schemas import DownloadRequest, DownloadStatus
from app.services.ytdlp_service import download_stream
from app.services.ffmpeg_service import merge
from app.utils.file_helper import (
    video_temp_path,
    audio_temp_path,
    final_output_path,
    cleanup_job_temp,
    file_size_mb,
)

router = APIRouter()

# in-memory job tracker (replaced by Redis later)
job_store: dict = {}


@router.post("/download", response_model=DownloadStatus)
async def download(req: DownloadRequest, bg: BackgroundTasks):
    """
    Accepts a download request and immediately returns job_id.
    The actual download runs in the background via BackgroundTasks.
    """
    job_store[req.job_id] = {"status": "queued", "message": "Job received"}
    bg.add_task(run_download_job, req)
    return DownloadStatus(job_id=req.job_id, status="queued", message="Download started in background")


@router.get("/status/{job_id}", response_model=DownloadStatus)
async def get_status(job_id: str):
    """Poll this to check job progress. Later replaced by WebSocket push."""
    job = job_store.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return DownloadStatus(job_id=job_id, **job)


# ─── Background Job ────────────────────────────────────────────────────────────

def run_download_job(req: DownloadRequest):
    video_path = video_temp_path(req.job_id)
    audio_path = audio_temp_path(req.job_id)
    final_path = final_output_path(req.job_id)

    try:
        job_store[req.job_id] = {"status": "downloading", "message": f"Downloading video stream (itag {req.video_itag})"}
        download_stream(req.url, req.video_itag, video_path)

        job_store[req.job_id] = {"status": "downloading", "message": f"Downloading audio stream (itag {req.audio_itag})"}
        download_stream(req.url, req.audio_itag, audio_path)

        job_store[req.job_id] = {"status": "merging", "message": "Merging video and audio with FFmpeg"}
        merge(video_path, audio_path, final_path)

        size = file_size_mb(final_path)
        job_store[req.job_id] = {"status": "done", "message": f"File ready — {size} MB"}
        print(f"[job {req.job_id}] ✅ complete → {final_path} ({size} MB)")

    except Exception as e:
        cleanup_job_temp(req.job_id)   # remove any half-downloaded temp files
        job_store[req.job_id] = {"status": "error", "message": str(e)}
        print(f"[job {req.job_id}] ❌ error → {e}")
