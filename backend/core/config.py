from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    PROJECT_NAME: str = "DISC Coupon Authority"
    API_V1_STR: str = "/v1"
    
    # Security
    # In real usage, this would be a private key for PASETO or similar
    SECRET_KEY: str = "dev_secret_key_change_in_production"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 5
    
    # Redis
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379

    # Policy Engine uses OPA
    OPA_URL: str = "http://localhost:8181"
    # For local dev without OPA, we can fail-open if needed (set to True)
    DEV_MODE: bool = False 

    # Kafka (Week 4 Features)
    KAFKA_BOOTSTRAP_SERVERS: str = "localhost:9092"
    KAFKA_TOPIC_AUDIT: str = "audit-logs"

    class Config:
        env_file = ".env"

settings = Settings()