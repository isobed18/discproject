import redis
from typing import List
from ..core.config import settings

# Initialize Redis connection (duplicated pattern for MVP)
try:
    redis_client = redis.Redis(
        host=settings.REDIS_HOST,
        port=settings.REDIS_PORT,
        decode_responses=True
    )
    redis_client.ping() # Check connection
except redis.exceptions.ConnectionError:
    print("WARNING: Redis not available for DelegationService, using in-memory mock.")
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
            pass # Mock doesn't handle TTL expiration actively
    redis_client = MockRedisDelegation()

def add_delegation(owner: str, delegate: str, resource: str, ttl: int = 3600):
    """
    Allow 'delegate' to act on 'resource' owned by 'owner'.
    In our model, we just store that 'delegate' has access to 'resource'.
    Key: "delegations:{resource}" -> Set(delegate_user_ids)
    
    Realistically we might want "delegations:{owner}:{resource}" but for week 3
    we follow the simplistic OPA rule checking `input.resource`.
    """
    key = f"delegations:{resource}"
    redis_client.sadd(key, delegate)
    # Note: Sets don't expire individually in Redis easily without logic, 
    # but we can expire the whole key if it's unique to the delegation.
    # For MVP with shared resource key, we won't set expiry on the set, 
    # or we accept that the resource delegation list expires entirely.
    # Let's just set expire for the whole resource list for now.
    redis_client.expire(key, ttl)

def get_delegations_for_resource(resource: str) -> List[str]:
    """
    Return list of users allowed to access this resource via delegation.
    """
    key = f"delegations:{resource}"
    # smembers returns a set
    members = redis_client.smembers(key)
    return list(members)
