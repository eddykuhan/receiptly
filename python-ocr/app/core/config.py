from pydantic_settings import BaseSettings
from functools import lru_cache

class Settings(BaseSettings):
    """Application settings"""
    
    # Azure Document Intelligence Settings
    AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT: str
    AZURE_DOCUMENT_INTELLIGENCE_KEY: str
    
    # API Settings
    API_PREFIX: str = "/api/v1"
    
    # CORS Settings
    CORS_ORIGINS: list = ["*"]
    CORS_HEADERS: list = ["*"]
    CORS_METHODS: list = ["*"]
    
    # Debug Settings
    DEBUG_IMAGE_PROCESSING: bool = False
    DEBUG_TESSERACT: bool = False
    DEBUG_OUTPUT_DIR: str = "debug_ocr"
    
    class Config:
        env_file = ".env"

@lru_cache()
def get_settings() -> Settings:
    """Get cached settings"""
    return Settings()