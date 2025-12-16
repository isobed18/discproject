import redis
from typing import List
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
            pass 
    redis_client = MockRedisDelegation()

def add_delegation(owner: str, delegate: str, resource: str, ttl: int = 3600):
    """
    Grants 'delegate' access to 'resource'.
    Data Structure: "delegations:{resource}" -> Set(delegate_user_ids)
    """
    key = f"delegations:{resource}"
    redis_client.sadd(key, delegate)
    
    # In this simplified model, we expire the whole resource delegation list.
    # In a production granular model, we would use sorted sets or individual keys.
    redis_client.expire(key, ttl)

def get_delegations_for_resource(resource: str) -> List[str]:
    """
    Returns a list of users who have been delegated access to this resource.
    """
    key = f"delegations:{resource}"
    members = redis_client.smembers(key)
    return list(members)