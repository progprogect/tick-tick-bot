"""
Date parsing utilities for converting natural language dates to ISO format
"""

from datetime import datetime, timedelta
from typing import Optional
import re


def parse_date(date_str: str) -> Optional[str]:
    """
    Parse natural language date to ISO 8601 format
    
    Args:
        date_str: Date string (e.g., "завтра", "tomorrow", "2024-11-05")
        
    Returns:
        ISO 8601 formatted date string or None
    """
    if not date_str:
        return None
    
    original_date_str = date_str.strip()
    date_str_lower = original_date_str.lower()
    today = datetime.now()
    
    # Relative dates - format will be converted to TickTick format by _format_date_for_ticktick
    # But we return ISO format with +00:00 which is then converted to +0000
    if date_str_lower in ["сегодня", "today"]:
        return today.strftime("%Y-%m-%dT00:00:00+00:00")
    
    if date_str_lower in ["завтра", "tomorrow"]:
        tomorrow = today + timedelta(days=1)
        return tomorrow.strftime("%Y-%m-%dT00:00:00+00:00")
    
    if date_str_lower in ["послезавтра", "day after tomorrow"]:
        day_after = today + timedelta(days=2)
        return day_after.strftime("%Y-%m-%dT00:00:00+00:00")
    
    if date_str_lower in ["вчера", "yesterday"]:
        yesterday = today - timedelta(days=1)
        return yesterday.strftime("%Y-%m-%dT00:00:00+00:00")
    
    # Try to parse ISO format (preserve original case)
    try:
        # If already in ISO format, return as is (preserve case)
        if "T" in original_date_str or "t" in original_date_str or "Z" in original_date_str or "+" in original_date_str or "-" in original_date_str[-6:]:
            # Check if it's a valid ISO format
            try:
                datetime.fromisoformat(original_date_str.replace("Z", "+00:00"))
                return original_date_str
            except:
                pass
    except:
        pass
    
    # Try parsing common formats
    formats = [
        "%Y-%m-%d",
        "%d.%m.%Y",
        "%d/%m/%Y",
        "%m/%d/%Y",
    ]
    
    for fmt in formats:
        try:
            parsed = datetime.strptime(date_str_lower, fmt)
            return parsed.strftime("%Y-%m-%dT00:00:00+00:00")
        except:
            continue
    
    # If can't parse, return None
    return None

