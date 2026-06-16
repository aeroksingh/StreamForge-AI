# StreamForge AI 🎬

> A full-stack YouTube video downloader built as a distributed system — Chrome Extension + Spring Boot + Python microservice + Redis + PostgreSQL.

![Status](https://img.shields.io/badge/status-active-success)
![Java](https://img.shields.io/badge/Java-21-orange)
![Python](https://img.shields.io/badge/Python-3.12-blue)
![Spring Boot](https://img.shields.io/badge/Spring%20Boot-3.3-green)
![License](https://img.shields.io/badge/license-MIT-blue)

---

## Why I Built This

There are already a dozen YouTube downloaders out there. I didn't need another one — I needed an excuse to build a real distributed system instead of one more CRUD app.

So instead of writing a single script that calls yt-dlp and exits, I forced myself to build it the way an actual backend would be built: a job queue between two languages, a database that remembers job state, a WebSocket channel pushing live updates to a client, and a Chrome extension on the other end consuming all of it.

Every piece exists because of a question I wanted answered for myself — how does YouTube actually serve a 4K video over HTTP? How do you keep a browser extension in sync with a job running in a completely different process and language? How does FFmpeg merge two separate streams without losing a single frame of sync? StreamForge AI is what came out of chasing those answers.

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
- ✅ **Downloads page** — one view inside the extension showing every job (active, completed, failed), backed by PostgreSQL
- ✅ Job history stored in PostgreSQL
- ✅ Redis job queue — non-blocking, async processing
- ✅ Save As dialog — user picks download location
- ✅ Quality selection — all available itags shown
- ✅ Playlist detection
- ✅ One-command local setup via `start.sh` / `stop.sh`

---

## Project Structure

```
youtube-downloader/
├── start.sh                        # One-command setup — Docker, Python service, worker, Spring Boot
├── stop.sh                         # Stops all services cleanly
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
    │   ├── popup.css
    │   ├── downloads.html          # Downloads page — full job history view
    │   └── downloads.js            # Fetches job list, renders status/progress
    ├── content/content.js          # YouTube page injection
    ├── background/background.js    # Badge + notifications
    └── icons/
```

---

## Setup & Run

### Quick Start (recommended)

```bash
git clone https://github.com/aeroksingh/StreamForge-AI.git
cd StreamForge-AI
./start.sh
```

`start.sh` brings up Docker (PostgreSQL + Redis), launches the Python FastAPI service and the Redis worker, and starts Spring Boot — in order, waiting for each to be healthy before moving to the next.

When you're done:

```bash
./stop.sh
```

This stops Spring Boot, the Python service, the worker, and tears down the Docker containers.

Then load the extension: `chrome://extensions/` → enable Developer mode → Load unpacked → select the `extension/` folder → open any YouTube video and click the StreamForge icon.

### Manual Setup (if you want to run each piece yourself)

**Prerequisites**

```bash
# Required
Java 21, Maven, Python 3.12, Docker, FFmpeg, Git

# Ubuntu/Debian
sudo apt install openjdk-21-jdk maven python3 python3-pip ffmpeg docker.io -y
```

**1. Start Docker (PostgreSQL + Redis)**

```bash
sudo docker compose up -d
```

**2. Python Service**

```bash
cd python-service
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python3 -m uvicorn app.main:app --reload --port 8001
```

**3. Python Worker** (new terminal)

```bash
cd python-service
source venv/bin/activate
python3 redis_worker.py
```

**4. Spring Boot**

```bash
cd spring-backend/backend
./mvnw spring-boot:run
```

**5. Chrome Extension**

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

Add these once you've run the project locally — they cover the parts that are hardest to explain in text:

| Screenshot | What to capture |
|---|---|
| Popup — Quality Selection | The itag/quality list right after a YouTube URL is detected |
| Live Progress | The popup mid-download — %, speed, ETA |
| Downloads Page | The full job history view inside the extension |
| Chrome Notification | The completion notification |

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

Built by Ashutosh.
