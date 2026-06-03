import redis
import json
import os
from dotenv import load_dotenv

load_dotenv()

REDIS_URL   = os.getenv("REDIS_URL", "redis://localhost:6379")
QUEUE_NAME  = "download_queue"
STATUS_PREFIX = "job_status:"

# single connection — reused across all calls
client = redis.from_url(REDIS_URL, decode_responses=True)


# ─── Connection Check ──────────────────────────────────────────────────────────

def ping() -> bool:
    """Returns True if Redis is reachable."""
    try:
        return client.ping()
    except Exception:
        return False


# ─── Job Status (replaces job_store dict) ─────────────────────────────────────

def set_status(job_id: str, status: str, message: str = ""):
    """
    Saves job status in Redis as a hash.
    Key format: job_status:{job_id}
    Expires after 1 hour automatically — no manual cleanup needed.
    """
    key = f"{STATUS_PREFIX}{job_id}"
    client.hset(key, mapping={"status": status, "message": message})
    client.expire(key, 3600)   # auto-delete after 1 hour


def get_status(job_id: str) -> dict | None:
    """
    Returns job status dict or None if job not found.
    """
    key = f"{STATUS_PREFIX}{job_id}"
    data = client.hgetall(key)
    return data if data else None


# ─── Job Queue (Spring Boot will push here later) ─────────────────────────────

def push_job(job: dict):
    """
    Pushes a job to the left of the Redis list (queue).
    Spring Boot will call this later — for now Python itself pushes for testing.
    """
    client.lpush(QUEUE_NAME, json.dumps(job))


def pop_job() -> dict | None:
    """
    Blocking pop from the right of the queue (FIFO order).
    Waits up to 5 seconds for a job — returns None if nothing arrives.
    Used by the worker to pull jobs.
    """
    result = client.brpop(QUEUE_NAME, timeout=5)
    if result:
        _, raw = result
        return json.loads(raw)
    return None
