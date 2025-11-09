from pydantic_settings import BaseSettings
from functools import lru_cache

class Settings(BaseSettings):
    """Application settings"""
    
    # Azure Document Intelligence Settings
    AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT: str
    AZURE_DOCUMENT_INTELLIGENCE_KEY: str
    
    # AWS S3 Settings
    AWS_ACCESS_KEY_ID: str
    AWS_SECRET_ACCESS_KEY: str
    AWS_S3_BUCKET_NAME: str
    AWS_REGION: str = "us-east-1"
    
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