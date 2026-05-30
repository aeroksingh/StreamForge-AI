from fastapi import APIRouter, HTTPException
from app.models.schemas import ExtractRequest
from app.services.ytdlp_service import (
    detect_url_type,
    extract_video_info,
    extract_playlist_info,
)

router = APIRouter()


@router.post("/extract")
async def extract(req: ExtractRequest):
    """
    Smart extract endpoint.
    Detects whether the URL is a single video, a playlist,
    or a video that is part of a playlist — and responds accordingly.
    """
    try:
        url_type = detect_url_type(req.url)

        if url_type == "playlist":
            # Return playlist index (fast — uses extract_flat)
            return extract_playlist_info(req.url)

        elif url_type == "video_in_playlist":
            # Tell the client to ask the user what they want
            return {
                "url_type": "video_in_playlist",
                "message": "This video is part of a playlist. Download only this video, or the full playlist?",
                "options": ["single", "playlist"],
                "url": req.url,
            }

        else:
            # Single video — return all available formats/itags
            return extract_video_info(req.url)

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
