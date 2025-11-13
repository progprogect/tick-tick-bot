"""
Date parsing utilities for converting natural language dates to ISO format
"""

from datetime import datetime, timedelta, timezone
from typing import Optional
from src.config.constants import USER_TIMEZONE_OFFSET, USER_TIMEZONE_STR


def parse_date(date_str: str) -> Optional[str]:
    """
    Parse natural language date to ISO 8601 format with UTC+3 timezone
    
    Args:
        date_str: Date string (e.g., "завтра", "tomorrow", "2024-11-05", "08.11.2025 10:00")
        
    Returns:
        ISO 8601 formatted date string with UTC+3 timezone (e.g., "2024-11-05T00:00:00+03:00") or None
    """
    if not date_str:
        return None
    
    original_date_str = date_str.strip()
    date_str_lower = original_date_str.lower()
    
    # Create UTC+3 timezone
    user_tz = timezone(timedelta(hours=USER_TIMEZONE_OFFSET))
    today = datetime.now(user_tz)
    
    # Relative dates - return with UTC+3 timezone
    if date_str_lower in ["сегодня", "today"]:
        return today.strftime("%Y-%m-%dT00:00:00+03:00")
    
    if date_str_lower in ["завтра", "tomorrow"]:
        tomorrow = today + timedelta(days=1)
        return tomorrow.strftime("%Y-%m-%dT00:00:00+03:00")
    
    if date_str_lower in ["послезавтра", "day after tomorrow"]:
        day_after = today + timedelta(days=2)
        return day_after.strftime("%Y-%m-%dT00:00:00+03:00")
    
    if date_str_lower in ["вчера", "yesterday"]:
        yesterday = today - timedelta(days=1)
        return yesterday.strftime("%Y-%m-%dT00:00:00+03:00")
    
    # Try to parse ISO format (preserve original case)
    try:
        # If already in ISO format with timezone, return as is
        if "T" in original_date_str or "t" in original_date_str or "Z" in original_date_str or "+" in original_date_str or "-" in original_date_str[-6:]:
            # Check if it's a valid ISO format
            try:
                datetime.fromisoformat(original_date_str.replace("Z", "+00:00"))
                return original_date_str
            except:
                pass
    except:
        pass
    
    # Try parsing formats with time: "DD.MM.YYYY HH:MM" or "DD.MM.YYYY HH:MM:SS"
    time_formats = [
        "%d.%m.%Y %H:%M:%S",  # 08.11.2025 10:00:00
        "%d.%m.%Y %H:%M",     # 08.11.2025 10:00
        "%Y-%m-%d %H:%M:%S",  # 2025-11-08 10:00:00
        "%Y-%m-%d %H:%M",     # 2025-11-08 10:00
    ]
    
    for fmt in time_formats:
        try:
            parsed = datetime.strptime(original_date_str, fmt)
            # Add UTC+3 timezone
            parsed = parsed.replace(tzinfo=user_tz)
            return parsed.strftime("%Y-%m-%dT%H:%M:%S+03:00")
        except:
            continue
    
    # Try parsing date-only formats
    date_formats = [
        "%Y-%m-%d",
        "%d.%m.%Y",
        "%d/%m/%Y",
        "%m/%d/%Y",
    ]
    
    for fmt in date_formats:
        try:
            parsed = datetime.strptime(date_str_lower, fmt)
            # Add UTC+3 timezone and set to midnight
            parsed = parsed.replace(tzinfo=user_tz)
            return parsed.strftime("%Y-%m-%dT00:00:00+03:00")
        except:
            continue
    
    # If can't parse, return None
    return None

