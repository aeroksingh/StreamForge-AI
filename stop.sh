#!/bin/bash

PROJECT_DIR="/run/media/ashutosh/in use/003_myprojects/streamforge ai/youtube-downloader"

echo "Stopping StreamForge AI..."

# Kill Python processes
pkill -f "uvicorn app.main:app" 2>/dev/null
pkill -f "redis_worker.py" 2>/dev/null

# Kill Spring Boot
pkill -f "spring-boot:run" 2>/dev/null
pkill -f "BackendApplication" 2>/dev/null

# Stop Docker
sudo docker compose -f "$PROJECT_DIR/docker-compose.yml" stop

echo "✓ All stopped."
