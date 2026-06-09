from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv
import os

from app.routes import extract, download
from app.utils.file_helper import ensure_dirs
from app.services.redis_service import ping

load_dotenv()
ensure_dirs()

app = FastAPI(title="YT Downloader — Python Service", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(extract.router,  tags=["Extract"])
app.include_router(download.router, tags=["Download"])

# absolute path — works from any directory
DOWNLOADS_DIR = os.path.join(os.path.dirname(__file__), "..", "downloads")
DOWNLOADS_DIR = os.path.abspath(DOWNLOADS_DIR)

if os.path.exists(DOWNLOADS_DIR):
    app.mount("/files", StaticFiles(directory=DOWNLOADS_DIR), name="files")

@app.get("/health", tags=["Health"])
def health():
    return {
        "status": "ok",
        "redis": "connected" if ping() else "disconnected"
    }