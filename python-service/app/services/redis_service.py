import redis
import json
import os
from dotenv import load_dotenv

load_dotenv()

REDIS_URL     = os.getenv("REDIS_URL", "redis://localhost:6379")
QUEUE_NAME    = "download_queue"
STATUS_PREFIX = "job_status:"

client = redis.from_url(REDIS_URL, decode_responses=True)


def ping() -> bool:
    try:
        return client.ping()
    except Exception:
        return False


# ── CHANGED: added percent/speed/eta/label kwargs ────────────────────────────

def set_status(job_id: str, status: str, message: str = "",
               percent: float = 0, speed: str = "--",
               eta: str = "--:--", label: str = ""):
    key = f"{STATUS_PREFIX}{job_id}"
    client.hset(key, mapping={
        "status":  status,
        "message": message,
        "percent": percent,
        "speed":   speed,
        "eta":     eta,
        "label":   label,
    })
    client.expire(key, 3600)


def get_status(job_id: str) -> dict | None:
    key = f"{STATUS_PREFIX}{job_id}"
    data = client.hgetall(key)
    return data if data else None


def push_job(job: dict):
    client.lpush(QUEUE_NAME, json.dumps(job))


def pop_job() -> dict | None:
    result = client.brpop(QUEUE_NAME, timeout=5)
    if result:
        _, raw = result
        return json.loads(raw)
    return None