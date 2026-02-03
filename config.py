"""Configuration for Blog Writing Agent."""

import os
from dotenv import load_dotenv

load_dotenv()

# Image generation provider: "google" or "openai"
# Google uses Imagen 3 (requires GOOGLE_API_KEY)
# OpenAI uses DALL-E 3 (requires OPENAI_API_KEY, which you already have)
IMAGE_PROVIDER = os.getenv("IMAGE_PROVIDER", "openai")  # Default to OpenAI

# LLM Configuration
LLM_MODEL = os.getenv("MODEL_NAME", "gpt-4o-mini")
LLM_TEMPERATURE = float(os.getenv("MODEL_TEMPERATURE", "0.7"))

# API Keys
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

# Validate configuration
def validate_config():
    """Validate that required API keys are present."""
    errors = []
    
    if not OPENAI_API_KEY:
        errors.append("OPENAI_API_KEY is required")
    
    if IMAGE_PROVIDER == "google" and not GOOGLE_API_KEY:
        errors.append("IMAGE_PROVIDER is 'google' but GOOGLE_API_KEY is not set")
    
    if errors:
        raise ValueError("\n".join(errors))
    
    return True
