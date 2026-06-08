from fastapi import FastAPI
from dotenv import load_dotenv
from app.routes import extract, download
from app.utils.file_helper import ensure_dirs
from app.services.redis_service import ping

load_dotenv()
ensure_dirs()

app = FastAPI(
    title="YT Downloader — Python Service",
    version="1.0.0",
)

app.include_router(extract.router,  tags=["Extract"])
app.include_router(download.router, tags=["Download"])


@app.get("/health", tags=["Health"])
def health():
    return {
        "status": "ok",
        "redis": "connected" if ping() else "disconnected"
    }


from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)
