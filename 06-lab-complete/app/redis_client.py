"""
Kết nối Redis dùng chung cho rate limiter và cost guard.
"""
import redis
from app.config import settings

_client = None


def get_redis_client():
    global _client
    if _client is None:
        try:
            _client = redis.from_url(
                settings.redis_url,
                decode_responses=True,
                socket_connect_timeout=1.0,
                socket_timeout=1.0,
            )
        except Exception:
            return None
    return _client


# Thuộc tính r để tương thích với code truy cập r trực tiếp
class RedisProxy:
    def __getattr__(self, name):
        client = get_redis_client()
        if client is None:
            raise redis.ConnectionError("Redis client is not available")
        return getattr(client, name)


r = RedisProxy()


def redis_healthy() -> bool:
    try:
        client = get_redis_client()
        if client is None:
            return False
        return bool(client.ping())
    except Exception:
        return False
