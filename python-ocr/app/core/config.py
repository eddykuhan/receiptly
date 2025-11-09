from pydantic_settings import BaseSettings
from functools import lru_cache

class Settings(BaseSettings):
    """Application settings"""
    
    # Azure Vision Settings
    AZURE_VISION_ENDPOINT: str
    AZURE_VISION_KEY: str
    
    # API Settings
    API_PREFIX: str = "/api/v1"
    
    # CORS Settings
    CORS_ORIGINS: list = ["*"]
    CORS_HEADERS: list = ["*"]
    CORS_METHODS: list = ["*"]
    
    class Config:
        env_file = ".env"

@lru_cache()
def get_settings() -> Settings:
    """Get cached settings"""
    return Settings()