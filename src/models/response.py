"""
Response model for bot responses
"""

from typing import Optional, List
from pydantic import BaseModel


class BotResponse(BaseModel):
    """Bot response model"""
    message: str
    success: bool = True
    data: Optional[dict] = None


class ErrorResponse(BaseModel):
    """Error response model"""
    message: str
    error_code: Optional[str] = None
    details: Optional[dict] = None
