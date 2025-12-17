import redis
from datetime import timedelta
# --- DÜZELTME: Absolute Import ---
from core.config import settings

try:
    redis_client = redis.Redis(
        host=settings.REDIS_HOST,
        port=settings.REDIS_PORT,
        decode_responses=True
    )
    redis_client.ping()
except Exception:
    class MockRedisRevoke:
        def __init__(self): self.store = {}
        def setex(self, k, t, v): self.store[k] = v
        def exists(self, k): return 1 if k in self.store else 0
    redis_client = MockRedisRevoke()

def revoke_jti(jti: str, ttl_seconds: int, reason: str = "revoked"):
    key = f"revoked:{jti}"
    redis_client.setex(key, timedelta(seconds=ttl_seconds), reason)

def is_jti_revoked(jti: str) -> bool:
    key = f"revoked:{jti}"
    return redis_client.exists(key) > 0