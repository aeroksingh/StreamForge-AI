# StreamForge AI 🎬

> A full-stack YouTube video downloader built as a distributed system — Chrome Extension + Spring Boot + Python microservice + Redis + PostgreSQL.

![Status](https://img.shields.io/badge/status-active-success)
![Java](https://img.shields.io/badge/Java-21-orange)
![Python](https://img.shields.io/badge/Python-3.12-blue)
![Spring Boot](https://img.shields.io/badge/Spring%20Boot-3.3-green)
![License](https://img.shields.io/badge/license-MIT-blue)

---

## What is this?

StreamForge AI is a production-grade YouTube downloader that works as a Chrome extension. Instead of a simple script, it's built as a proper distributed system — the kind of architecture you'd find in real-world backend engineering.

When you click download on any YouTube video, here's what actually happens:

```
Chrome Extension
    ↓ POST /api/download/start
Spring Boot (Job Orchestrator)
    ↓ saves job to PostgreSQL
    ↓ pushes to Redis queue
Python Worker (pulls from queue)
    ↓ yt-dlp fetches DASH stream URLs
    ↓ downloads video stream (itag 137) in parallel
    ↓ downloads audio stream (itag 140) in parallel
    ↓ FFmpeg merges both streams
    ↓ writes progress to Redis
Spring Boot (@Scheduled every 2s)
    ↓ reads Redis progress
    ↓ updates PostgreSQL
    ↓ pushes WebSocket event
Chrome Extension
    ↓ shows live % + ETA + speed
    ↓ triggers Save As dialog on completion
```

---

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                   Chrome Extension                      │
│         Manifest V3 · content.js · popup.js             │
│         background.js (badge + notifications)           │
└──────────────────────┬──────────────────────────────────┘
                       │ HTTP REST
┌──────────────────────▼──────────────────────────────────┐
│              Spring Boot Backend :8080                  │
│   REST API · Job Orchestration · WebSocket · Security   │
│         PostgreSQL (JPA/Hibernate) · Redis pub/sub      │
└────────────┬─────────────────────────────┬──────────────┘
             │ Redis Queue                 │ WebSocket
┌────────────▼────────────┐   ┌────────────▼──────────────┐
│   Python Microservice   │   │     Chrome Extension      │
│      FastAPI :8001      │   │   (progress updates)      │
│  yt-dlp · FFmpeg        │   └──────────────────────────-┘
│  redis_worker.py        │
└─────────────────────────┘
             │
┌────────────▼────────────┐
│   Docker Containers     │
│  PostgreSQL :5432       │
│  Redis :6379            │
└─────────────────────────┘
```

---

## Tech Stack

| Layer | Technology | Purpose |
|---|---|---|
| Extension | JavaScript, Chrome Extension API, Manifest V3 | UI, video detection, download trigger |
| Backend | Spring Boot 3.3, Java 21 | REST API, job orchestration, auth |
| Database | PostgreSQL + JPA/Hibernate | Job history, user records |
| Cache/Queue | Redis | Job queue, real-time progress |
| Microservice | FastAPI, Python 3.12 | Stream extraction, download, merge |
| Downloader | yt-dlp | YouTube DASH/HLS stream parsing |
| Media | FFmpeg | Video + audio stream merge |
| Real-time | WebSocket (STOMP) | Live progress to extension |
| Containers | Docker + Docker Compose | PostgreSQL + Redis |

---

## Computer Networking Concepts Used

This project is a practical implementation of CN concepts:

- **HTTP/HTTPS** — REST API communication between all layers
- **TCP/IP** — understanding how YouTube video arrives as 1460-byte TCP segments
- **DASH Protocol** — Dynamic Adaptive Streaming over HTTP (how YouTube serves video)
- **Range Requests** — fetching video in chunks (`Range: bytes=0-524287`)
- **WebSockets** — full-duplex progress updates (STOMP over SockJS)
- **Redis Pub/Sub** — inter-service messaging
- **Client-Server Architecture** — extension as client, Spring Boot as server
- **CDN concepts** — YouTube's `googlevideo.com` CDN origin tracing
- **Packet analysis** — Wireshark inspection of video stream packets
- **Port management** — 8080 (Spring), 8001 (Python), 6379 (Redis), 5432 (PostgreSQL)

---

## Features

- ✅ Download any YouTube video (144p to 4K)
- ✅ Real-time progress — live %, speed, ETA in extension popup
- ✅ Background tracking — badge on extension icon even when popup is closed
- ✅ Chrome notifications on download complete
- ✅ Video + audio separate streams merged via FFmpeg
- ✅ Job history stored in PostgreSQL
- ✅ Redis job queue — non-blocking, async processing
- ✅ Save As dialog — user picks download location
- ✅ Quality selection — all available itags shown
- ✅ Playlist detection

---

## Project Structure

```
youtube-downloader/
├── docker-compose.yml              # PostgreSQL + Redis
│
├── python-service/                 # FastAPI microservice
│   ├── app/
│   │   ├── main.py                 # FastAPI entry point + CORS
│   │   ├── models/schemas.py       # Pydantic request/response models
│   │   ├── routes/
│   │   │   ├── extract.py          # POST /extract — fetch itags
│   │   │   └── download.py         # POST /download — start job
│   │   ├── services/
│   │   │   ├── ytdlp_service.py    # yt-dlp wrapper + progress hooks
│   │   │   ├── ffmpeg_service.py   # FFmpeg merge + zip
│   │   │   └── redis_service.py    # Redis queue + status
│   │   └── utils/file_helper.py    # Path management + cleanup
│   ├── redis_worker.py             # Standalone Redis queue worker
│   └── requirements.txt
│
├── spring-backend/backend/         # Spring Boot
│   └── src/main/java/com/streamforge/backend/
│       ├── controller/DownloadController.java
│       ├── service/
│       │   ├── DownloadService.java         # Job lifecycle
│       │   ├── RedisQueueService.java       # Queue push + progress read
│       │   └── WebSocketProgressService.java
│       ├── entity/DownloadJob.java
│       ├── repository/DownloadJobRepository.java
│       ├── config/
│       │   ├── RedisConfig.java
│       │   ├── WebSocketConfig.java
│       │   └── SecurityConfig.java
│       └── dto/
│           ├── DownloadRequestDto.java
│           └── JobResponseDto.java
│
└── extension/                      # Chrome Extension
    ├── manifest.json               # Manifest V3
    ├── popup/
    │   ├── popup.html
    │   ├── popup.js                # Quality select, download, polling
    │   └── popup.css
    ├── content/content.js          # YouTube page injection
    ├── background/background.js    # Badge + notifications
    └── icons/
```

---

## Setup & Run

### Prerequisites

```bash
# Required
Java 21, Maven, Python 3.12, Docker, FFmpeg, Git

# Ubuntu/Debian
sudo apt install openjdk-21-jdk maven python3 python3-pip ffmpeg docker.io -y
```

### 1. Clone

```bash
git clone https://github.com/your-username/streamforge-ai.git
cd streamforge-ai
```

### 2. Start Docker (PostgreSQL + Redis)

```bash
sudo docker compose up -d
```

### 3. Python Service

```bash
cd python-service
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python3 -m uvicorn app.main:app --reload --port 8001
```

### 4. Python Worker (new terminal)

```bash
cd python-service
source venv/bin/activate
python3 redis_worker.py
```

### 5. Spring Boot

```bash
cd spring-backend/backend
./mvnw spring-boot:run
```

### 6. Chrome Extension

```
1. Open Chrome → chrome://extensions/
2. Enable Developer mode
3. Load unpacked → select extension/ folder
4. Open any YouTube video → click StreamForge icon
```

---

## API Reference

### Python Service `:8001`

| Method | Endpoint | Description |
|---|---|---|
| GET | `/health` | Service + Redis status |
| POST | `/extract` | Fetch available formats for a YouTube URL |
| POST | `/download` | Start download job |
| GET | `/status/{jobId}` | Poll job progress |
| GET | `/files/{filename}` | Serve final mp4 |

### Spring Boot `:8080`

| Method | Endpoint | Description |
|---|---|---|
| POST | `/api/download/start` | Create job, push to Redis |
| GET | `/api/download/status/{jobId}` | Get job status from DB |
| GET | `/api/download/history` | User's download history |
| GET | `/api/download/file/{jobId}` | Serve completed file |
| GET | `/api/health` | Health check |

---

## How YouTube Download Actually Works

YouTube does not serve a single file. For 1080p and above:

1. **TLS Handshake** — browser connects to YouTube on port 443
2. **Manifest Request** — `GET /videoplayback?itag=137` — fetch available streams
3. **DASH Segments** — `Range: bytes=0-524287` — video arrives in ~2s chunks
4. **TCP Segments** — each HTTP response split into ~1460-byte TCP segments
5. **Two parallel streams** — video-only (itag 137) + audio-only (itag 140)
6. **FFmpeg merge** — PTS timestamps sync video + audio perfectly
7. **`-c:v copy -c:a copy`** — no re-encoding, just remux — takes ~2 seconds

---

## Environment Variables

Create `python-service/.env`:

```env
REDIS_URL=redis://localhost:6379
DOWNLOAD_DIR=downloads
TEMP_DIR=temp
```

`application.properties` (Spring Boot):

```properties
spring.datasource.url=jdbc:postgresql://localhost:5432/ytdownloader
spring.datasource.username=admin
spring.datasource.password=admin123
spring.data.redis.host=localhost
spring.data.redis.port=6379
app.python.service.url=http://localhost:8001
app.websocket.allowed-origins=*
```

---

## Screenshots

> Add screenshots here after running the project locally.

---

## What I Learned Building This

- Distributed system design — separating concerns across services
- DASH/HLS streaming protocols and how video is actually delivered
- Redis as a job queue and pub/sub message broker
- Spring Boot async job processing with `@Scheduled` and `@Async`
- Chrome Extension Manifest V3 — content scripts, service workers, storage API
- FFmpeg stream remuxing — why `-c copy` works without quality loss
- Real-time communication — WebSocket with STOMP protocol
- Docker for local service orchestration

---

## Future Improvements

- [ ] Playlist download support
- [ ] Resume interrupted downloads
- [ ] Cloud deployment (Railway + Upstash + Neon)
- [ ] User authentication
- [ ] Download speed optimization (parallel chunks)
- [ ] Mobile app (React Native)

---

## License

MIT — use freely, credit appreciated.

---

*Built by Ashutosh — learning distributed systems by building one.*
