"""
Application settings and configuration
"""

import os
from pathlib import Path
from dotenv import load_dotenv
from typing import Optional

# Load environment variables from .env file
env_path = Path(__file__).parent.parent.parent / ".env"
load_dotenv(dotenv_path=env_path)


class Settings:
    """Application settings loaded from environment variables"""
    
    # Telegram Bot
    TELEGRAM_BOT_TOKEN: str = os.getenv("TELEGRAM_BOT_TOKEN", "")
    
    # OpenAI
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    USE_WHISPER: bool = os.getenv("USE_WHISPER", "false").lower() == "true"
    
    # TickTick
    TICKTICK_EMAIL: str = os.getenv("TICKTICK_EMAIL", "")
    TICKTICK_PASSWORD: str = os.getenv("TICKTICK_PASSWORD", "")
    TICKTICK_ACCESS_TOKEN: Optional[str] = os.getenv("TICKTICK_ACCESS_TOKEN", None)
    TICKTICK_CLIENT_ID: Optional[str] = os.getenv("TICKTICK_CLIENT_ID", None)
    TICKTICK_CLIENT_SECRET: Optional[str] = os.getenv("TICKTICK_CLIENT_SECRET", None)
    
    # Database
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./ticktick_bot.db")
    
    # Application
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    WEB_PORT: int = int(os.getenv("WEB_PORT", "8000"))
    
    @classmethod
    def validate(cls) -> bool:
        """Validate that all required settings are present"""
        required = [
            cls.TELEGRAM_BOT_TOKEN,
            cls.OPENAI_API_KEY,
            cls.TICKTICK_EMAIL,
            cls.TICKTICK_PASSWORD,
        ]
        
        missing = [field for field in required if not field]
        
        if missing:
            raise ValueError(
                f"Missing required environment variables: {', '.join(missing)}"
            )
        
        return True


# Global settings instance
settings = Settings()

