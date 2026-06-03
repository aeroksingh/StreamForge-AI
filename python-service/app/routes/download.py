from fastapi import APIRouter, BackgroundTasks, HTTPException
from app.models.schemas import DownloadRequest, DownloadStatus
from app.services.ytdlp_service import download_stream
from app.services.ffmpeg_service import merge
from app.services.redis_service import set_status, get_status
from app.utils.file_helper import (
    video_temp_path, audio_temp_path,
    final_output_path, cleanup_job_temp, file_size_mb,
)

router = APIRouter()


@router.post("/download", response_model=DownloadStatus)
async def download(req: DownloadRequest, bg: BackgroundTasks):
    set_status(req.job_id, "queued", "Job received")
    bg.add_task(run_download_job, req)
    return DownloadStatus(job_id=req.job_id, status="queued", message="Download started")


@router.get("/status/{job_id}", response_model=DownloadStatus)
async def get_job_status(job_id: str):
    job = get_status(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return DownloadStatus(job_id=job_id, **job)


def run_download_job(req: DownloadRequest):
    video_path = video_temp_path(req.job_id)
    audio_path = audio_temp_path(req.job_id)
    final_path = final_output_path(req.job_id)

    try:
        set_status(req.job_id, "downloading", f"Downloading video stream (itag {req.video_itag})")
        download_stream(req.url, req.video_itag, video_path)

        set_status(req.job_id, "downloading", f"Downloading audio stream (itag {req.audio_itag})")
        download_stream(req.url, req.audio_itag, audio_path)

        set_status(req.job_id, "merging", "Merging with FFmpeg")
        merge(video_path, audio_path, final_path)

        size = file_size_mb(final_path)
        set_status(req.job_id, "done", f"File ready — {size} MB")
        print(f"[job {req.job_id}] done → {final_path}")

    except Exception as e:
        cleanup_job_temp(req.job_id)
        set_status(req.job_id, "error", str(e))
        print(f"[job {req.job_id}] error → {e}")
