"""
Rate limiting (tiêu chí 7).
"""
import time
import uuid
from fastapi import HTTPException
from app.config import settings
from app.redis_client import r


def check_rate_limit(key: str) -> None:
    now = time.time()
    window_start = now - 60
    redis_key = f"rate_limit:{key}"

    try:
        # Xóa các request cũ ngoài cửa sổ 60s
        r.zremrangebyscore(redis_key, 0, window_start)
        # Đếm số lượng request hiện tại trong cửa sổ
        current_count = r.zcard(redis_key)

        if current_count >= settings.rate_limit_per_minute:
            raise HTTPException(
                status_code=429,
                detail="Rate limit exceeded",
                headers={"Retry-After": "60"},
            )

        # Ghi nhận request mới với id duy nhất để ZCARD tăng chuẩn xác
        member = f"{now}:{uuid.uuid4().hex[:8]}"
        r.zadd(redis_key, {member: now})
        r.expire(redis_key, 60)
    except HTTPException:
        raise
    except Exception:
        # Nếu Redis lỗi tạm thời, không chặn request
        pass
