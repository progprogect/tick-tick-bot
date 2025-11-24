"""
Centralized date/time utilities for UTC+3 timezone
All date/time operations should use functions from this module
"""

from datetime import datetime, timezone, timedelta
from typing import Optional
from src.config.constants import USER_TIMEZONE_OFFSET, USER_TIMEZONE_STR

# Singleton timezone object
USER_TIMEZONE = timezone(timedelta(hours=USER_TIMEZONE_OFFSET))


def get_current_datetime() -> datetime:
    """
    Get current datetime in UTC+3 timezone
    
    Returns:
        Current datetime object with UTC+3 timezone
    """
    return datetime.now(USER_TIMEZONE)


def get_current_date_str() -> str:
    """
    Get current date string in UTC+3 (YYYY-MM-DD)
    
    Returns:
        Current date as string in format YYYY-MM-DD
    """
    return get_current_datetime().strftime("%Y-%m-%d")


def get_current_datetime_str() -> str:
    """
    Get current datetime string in UTC+3 (YYYY-MM-DD HH:MM:SS)
    
    Returns:
        Current datetime as string in format YYYY-MM-DD HH:MM:SS
    """
    return get_current_datetime().strftime("%Y-%m-%d %H:%M:%S")


def get_current_datetime_for_gpt() -> str:
    """
    Get current datetime formatted for GPT prompts
    
    Format: "YYYY-MM-DD (YYYY-MM-DD HH:MM:SS)"
    Example: "2025-11-13 (2025-11-13 15:30:45)"
    
    Returns:
        Formatted datetime string for GPT prompts
    """
    dt = get_current_datetime()
    return f"{dt.strftime('%Y-%m-%d')} ({dt.strftime('%Y-%m-%d %H:%M:%S')})"

