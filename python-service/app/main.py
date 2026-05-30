from fastapi import FastAPI
from dotenv import load_dotenv
from app.routes import extract, download

load_dotenv()  # loads .env file

app = FastAPI(
    title="YT Downloader — Python Service",
    description="Handles stream extraction, download, and FFmpeg merge.",
    version="1.0.0",
)

# Register routes
app.include_router(extract.router,  tags=["Extract"])
app.include_router(download.router, tags=["Download"])


@app.get("/health", tags=["Health"])
def health():
    return {"status": "ok", "service": "python-service"}
