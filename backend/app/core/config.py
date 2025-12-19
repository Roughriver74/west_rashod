"""Application configuration."""
from typing import List, Optional
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings."""

    # Application
    APP_NAME: str = "West Rashod - Bank Transactions"
    DEBUG: bool = True
    API_PREFIX: str = "/api/v1"

    # Database
    DATABASE_URL: str = "postgresql://rashod_user:rashod_pass@localhost:54330/west_rashod_db"

    # Security
    SECRET_KEY: str = "west-rashod-secret-key-change-in-production-min-32-chars"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # CORS
    CORS_ORIGINS: str = '["http://localhost:5174","http://localhost:3000"]'

    @property
    def cors_origins_list(self) -> List[str]:
        """Parse CORS origins from string."""
        import json
        try:
            return json.loads(self.CORS_ORIGINS)
        except:
            return ["http://localhost:5174", "http://localhost:3000"]

    # 1C OData Integration
    ODATA_1C_URL: str = "http://10.10.100.77/trade/odata/standard.odata"
    ODATA_1C_USERNAME: str = "odata.user"
    ODATA_1C_PASSWORD: str = "ak228Hu2hbs28"
    ODATA_1C_CUSTOM_AUTH_TOKEN: Optional[str] = None

    # OData Timeouts
    ODATA_REQUEST_TIMEOUT: int = 60
    ODATA_CONNECTION_TIMEOUT: int = 10
    ODATA_GET_REQUEST_TIMEOUT: int = 30

    # Batch size
    SYNC_BATCH_SIZE: int = 100

    # Redis
    USE_REDIS: bool = False
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6380

    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "allow"


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


settings = get_settings()
