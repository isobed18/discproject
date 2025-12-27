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

    # Encryption (Week 4)
    # 32 url-safe base64-encoded bytes. Default is for dev only.
    FIELD_ENCRYPTION_KEY: str = "Jd87wj9L_f83mK-74sS2-d9f0_k3nC83_w84mF93kD0=" 

    # PASETO signing keys (Week 5 SDK offline mode support)
    # If not provided, keys are generated in-memory at startup (MVP).
    PASETO_PRIVATE_KEY_PEM: Optional[str] = None
    PASETO_PUBLIC_KEY_PEM: Optional[str] = None
    PASETO_PRIVATE_KEY_PATH: Optional[str] = None
    PASETO_PUBLIC_KEY_PATH: Optional[str] = None


    class Config:
        env_file = ".env"

settings = Settings()