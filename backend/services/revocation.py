import redis
from ..core.config import settings

# Initialize Redis connection
redis_client = redis.Redis(
    host=settings.REDIS_HOST,
    port=settings.REDIS_PORT,
    decode_responses=True
)

def revoke_jti(jti: str, ttl_seconds: int, reason: str = "revoked"):
    """
    Add a JTI to the revocation list with a TTL.
    """
    key = f"revoked:{jti}"
    redis_client.setex(key, ttl_seconds, reason)

def is_jti_revoked(jti: str) -> bool:
    """
    Check if a JTI is in the revocation list.
    """
    key = f"revoked:{jti}"
    return redis_client.exists(key) > 0
