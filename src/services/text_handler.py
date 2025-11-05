"""
Text message handler
"""

from typing import Optional
from src.utils.logger import logger


class TextHandler:
    """Handler for text messages"""
    
    def __init__(self):
        """Initialize text handler"""
        self.logger = logger
    
    def process(self, text: str) -> str:
        """
        Process text message
        
        Args:
            text: Text message
            
        Returns:
            Processed text (trimmed and normalized)
        """
        # Trim whitespace
        processed = text.strip()
        
        # Remove extra whitespace
        processed = " ".join(processed.split())
        
        self.logger.debug(f"Processed text: {processed}")
        
        return processed
    
    def validate(self, text: str) -> bool:
        """
        Validate text message
        
        Args:
            text: Text message
            
        Returns:
            True if valid, False otherwise
        """
        if not text or not text.strip():
            return False
        
        # Check length (Telegram max is 4096)
        if len(text) > 4096:
            return False
        
        return True


