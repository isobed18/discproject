from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    PROJECT_NAME: str = "DISC Coupon Authority"
    API_V1_STR: str = "/v1"
    
    # Security Keys (Should be loaded from Vault/Secrets in production)
    SECRET_KEY: str = "dev_secret_key_change_in_production"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 5
    
    # Redis Configuration
    REDIS_HOST: str = "redis" # Use 'localhost' if running without Docker
    REDIS_PORT: int = 6379

    # OPA (Policy Engine) Configuration
    # URL points to the OPA service defined in docker-compose
    OPA_URL: str = "http://opa:8181/v1/data/disc/authz/allow"
    
    # DEV_MODE: If True, it allows requests even if OPA is unreachable (Fail-Open)
    # Set to False for Production (Fail-Closed)
    DEV_MODE: bool = True 
    
    # Kafka Configuration
    KAFKA_BOOTSTRAP_SERVERS: str = "localhost:9092" 
  
    KAFKA_TOPIC_AUDIT: str = "disc-audit-logs"

    class Config:
        env_file = ".env"

settings = Settings()