import redis
import logging
from typing import List

# --- DÜZELTME: Absolute Import ---
from core.config import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Redis Connection
try:
    redis_client = redis.Redis(
        host=settings.REDIS_HOST,
        port=settings.REDIS_PORT,
        decode_responses=True
    )
    redis_client.ping()
    logger.info(f"✅ Delegation Service connected to Redis at {settings.REDIS_HOST}")
except Exception as e:
    logger.warning(f"⚠️ Redis not available ({e}), using in-memory mock.")
    class MockRedisDelegation:
        def __init__(self):
            self.store = {}
        def sadd(self, key, *values):
            if key not in self.store:
                self.store[key] = set()
            for v in values:
                self.store[key].add(v)
        def smembers(self, key):
            return self.store.get(key, set())
        def expire(self, key, ttl):
            pass 
    redis_client = MockRedisDelegation()

def add_delegation(owner: str, delegate: str, resource: str, ttl: int = 3600):
    key = f"delegations:{resource}"
    redis_client.sadd(key, delegate)
    redis_client.expire(key, ttl)
    logger.info(f"➕ Delegation ADDED: {delegate} -> {resource}")

def get_delegations_for_resource(resource: str) -> List[str]:
    key = f"delegations:{resource}"
    members = redis_client.smembers(key)
    
    decoded_members = []
    if members:
        for m in members:
            val = m.decode('utf-8') if isinstance(m, bytes) else str(m)
            decoded_members.append(val)
            
    logger.info(f"🔍 Delegation LOOKUP for {resource}: Found {decoded_members}")
    return decoded_members