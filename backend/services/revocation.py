import redis
from ..core.config import settings

# Initialize Redis connection
try:
    redis_client = redis.Redis(
        host=settings.REDIS_HOST,
        port=settings.REDIS_PORT,
        decode_responses=True
    )
    redis_client.ping() # Check connection
except redis.exceptions.ConnectionError:
    print("WARNING: Redis not available, using in-memory mock.")
    class MockRedis:
        def __init__(self):
            self.store = {}
        def setex(self, key, time, value):
            self.store[key] = value
        def exists(self, key):
            return 1 if key in self.store else 0
    redis_client = MockRedis()

def revoke_jti(jti: str, ttl_seconds: int, reason: str = "revoked"):
    """
    Adds a JTI (JSON Token Identifier) to the revocation list (Redis) with a TTL.
    This effectively blacklists the token until it naturally expires.
    """
    key = f"revoked:{jti}"
    redis_client.setex(key, ttl_seconds, reason)

def is_jti_revoked(jti: str) -> bool:
    """
    Checks if a JTI exists in the revocation list.
    Returns: True if revoked, False otherwise.
    """
    key = f"revoked:{jti}"
    return redis_client.exists(key) > 0