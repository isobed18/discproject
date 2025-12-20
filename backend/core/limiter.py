from slowapi import Limiter
from slowapi.util import get_remote_address

# Singleton Limiter instance to be used across the app
limiter = Limiter(key_func=get_remote_address)
