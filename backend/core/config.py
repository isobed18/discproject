from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    PROJECT_NAME: str = "DISC Coupon Authority"
    API_V1_STR: str = "/v1"
    
    # Security
    SECRET_KEY: str = "dev_secret_key_change_in_production" # In real usage, this would be a private key for PASETO
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 5
    
    # Redis
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379

    # Policy Engine uses OPA
    OPA_URL: str = "http://localhost:8181/v1/data/disc/authz"
    DEV_MODE: bool = False # For local dev without OPA, we fail-open

    
    class Config:
        env_file = ".env"

settings = Settings()
