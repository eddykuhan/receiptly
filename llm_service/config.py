"""
Configuration module - loads environment variables.
This module should be imported first before any other modules that need env vars.
"""
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()
