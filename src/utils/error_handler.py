"""
Error handling utilities
"""

from typing import Optional
from src.models.response import ErrorResponse
from src.utils.logger import logger


class BotError(Exception):
    """Base exception for bot errors"""
    pass


class APIError(BotError):
    """API error exception"""
    def __init__(self, message: str, error_code: Optional[str] = None):
        self.message = message
        self.error_code = error_code
        super().__init__(self.message)


class ValidationError(BotError):
    """Validation error exception"""
    pass


def handle_error(error: Exception) -> ErrorResponse:
    """
    Handle error and return user-friendly message
    
    Args:
        error: Exception to handle
        
    Returns:
        ErrorResponse with user-friendly message
    """
    logger.error(f"Error occurred: {error}", exc_info=True)
    
    if isinstance(error, APIError):
        return ErrorResponse(
            message=f"Ошибка API: {error.message}",
            error_code=error.error_code,
        )
    
    if isinstance(error, ValidationError):
        return ErrorResponse(
            message=f"Ошибка валидации: {str(error)}",
        )
    
    # Generic error message
    return ErrorResponse(
        message="Произошла ошибка. Попробуйте позже или обратитесь к администратору.",
    )


def format_error_message(error: Exception) -> str:
    """
    Format error message for user
    
    Args:
        error: Exception to format
        
    Returns:
        User-friendly error message
    """
    error_response = handle_error(error)
    return error_response.message


