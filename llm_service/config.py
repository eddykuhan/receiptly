"""
Configuration module - loads environment variables.
This module should be imported first before any other modules that need env vars.
"""
from pydantic_settings import BaseSettings
from functools import lru_cache

class Settings(BaseSettings):
    """Application settings"""
    
    # LLM Provider Configuration
    USE_GROQ: bool = False
    
    # OpenAI Configuration
    OPENAI_API_KEY: str = ""
    MODEL_NAME: str = "gpt-4o-mini"
    
    # Groq Configuration
    GROQ_API_KEY: str = ""
    
    # Server Configuration
    HOST: str = "0.0.0.0"
    PORT: int = 8500
    
    class Config:
        env_file = ".env"

@lru_cache()
def get_settings() -> Settings:
    """Get cached settings"""
    return Settings()
