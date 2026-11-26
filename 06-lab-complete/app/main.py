"""
Production AI Agent — Part 6 Final Project
"""
import json
import logging
import time
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import Depends, FastAPI, HTTPException, Query, Request
from pydantic import BaseModel, Field

from app.auth import verify_api_key
from app.config import settings
from app.cost_guard import check_budget, record_cost
from app.rate_limiter import check_rate_limit
from app.redis_client import redis_healthy
from utils.mock_llm import ask as llm_ask


# ── Structured Logging (JSON Formatter) ───────────────────────
class JsonFormatter(logging.Formatter):
    def format(self, record):
        log_obj = {
            "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(record.created)),
            "lvl": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
        }
        if record.exc_info:
            log_obj["exc_info"] = self.formatException(record.exc_info)
        return json.dumps(log_obj)


handler = logging.StreamHandler()
handler.setFormatter(JsonFormatter())

logger = logging.getLogger("app")
logger.handlers = [handler]
logger.setLevel(logging.INFO)
logger.propagate = False


# ── Lifespan for Graceful Shutdown ───────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Application starting up")
    yield
    logger.info("Application shutting down gracefully")


app = FastAPI(title="Production AI Agent", lifespan=lifespan)


class AskRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=2000)
    user_id: Optional[str] = None


# ── Health & Readiness Endpoints ──────────────────────────────
@app.get("/health")
def health():
    """Liveness check: Luôn trả 200 khi tiến trình còn sống."""
    return {"status": "ok"}


@app.get("/ready")
def ready():
    """Readiness check: Trả 200 nếu kết nối Redis ok, 503 nếu mất kết nối."""
    if not redis_healthy():
        raise HTTPException(status_code=503, detail="Redis connection failed")
    return {"status": "ready"}


# ── Main Ask Endpoint ─────────────────────────────────────────
@app.post("/ask")
def ask(
    request: Request,
    body: Optional[AskRequest] = None,
    question: Optional[str] = Query(None),
    api_key: str = Depends(verify_api_key),
):
    # Lấy câu hỏi từ body hoặc query param
    q = ""
    if body and body.question:
        q = body.question
    elif question:
        q = question
    else:
        raise HTTPException(status_code=422, detail="Missing question")

    # Kiểm tra Rate Limit (429 nếu vượt)
    check_rate_limit(api_key)

    # Kiểm tra Budget (402 nếu hết ngân sách)
    check_budget()

    start_time = time.time()
    answer = llm_ask(q)
    latency_ms = (time.time() - start_time) * 1000

    # Ghi nhận chi phí token
    record_cost(len(q.split()), len(answer.split()))

    logger.info(f"Answered request successfully in {latency_ms:.1f}ms")

    return {"question": q, "answer": answer}
