"""
Voice message handler
"""

from typing import Optional
from src.api.openai_client import OpenAIClient
from src.config.settings import settings
from src.utils.logger import logger


class VoiceHandler:
    """Handler for voice messages"""
    
    def __init__(self):
        """Initialize voice handler"""
        self.openai_client = OpenAIClient()
        self.use_whisper = settings.USE_WHISPER
        self.logger = logger
    
    async def transcribe(self, voice_data: bytes, filename: str = "voice.ogg") -> str:
        """
        Transcribe voice message to text
        
        Args:
            voice_data: Voice file bytes
            filename: Voice file name with extension
            
        Returns:
            Transcribed text
            
        Raises:
            Exception: If transcription fails
        """
        try:
            self.logger.debug(f"Transcribing voice message: {filename}")
            
            if self.use_whisper:
                # Use OpenAI Whisper API
                text = await self.openai_client.transcribe_audio(voice_data, filename)
            else:
                # Use Telegram's built-in speech recognition
                # For now, we'll use Whisper as fallback
                text = await self.openai_client.transcribe_audio(voice_data, filename)
            
            self.logger.info(f"Transcribed text: {text}")
            
            return text
            
        except Exception as e:
            self.logger.error(f"Error transcribing voice: {e}", exc_info=True)
            raise ValueError("Не удалось распознать голос. Попробуйте повторить команду.")
