"""
Tests for date parser
"""

import pytest
from datetime import datetime, timedelta
from src.utils.date_parser import parse_date


def test_parse_today():
    """Test parsing 'today'"""
    result = parse_date("сегодня")
    assert result is not None
    assert "T00:00:00" in result


def test_parse_tomorrow():
    """Test parsing 'tomorrow'"""
    result = parse_date("завтра")
    assert result is not None
    tomorrow = datetime.now() + timedelta(days=1)
    assert tomorrow.strftime("%Y-%m-%d") in result


def test_parse_yesterday():
    """Test parsing 'yesterday'"""
    result = parse_date("вчера")
    assert result is not None
    yesterday = datetime.now() - timedelta(days=1)
    assert yesterday.strftime("%Y-%m-%d") in result


def test_parse_iso_format():
    """Test parsing ISO format date"""
    iso_date = "2024-11-05T00:00:00+00:00"
    result = parse_date(iso_date)
    assert result == iso_date


def test_parse_date_format():
    """Test parsing date in YYYY-MM-DD format"""
    result = parse_date("2024-11-05")
    assert result is not None
    assert "2024-11-05" in result


def test_parse_invalid_date():
    """Test parsing invalid date returns None"""
    result = parse_date("invalid date")
    assert result is None


