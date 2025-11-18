"""
Tests for task cache service
"""

import pytest
import json
from pathlib import Path
from src.services.task_cache import TaskCacheService


def test_cache_save_and_get_task(tmp_path):
    """Test saving and retrieving task from cache"""
    cache_file = tmp_path / "test_cache.json"
    cache = TaskCacheService(cache_file=str(cache_file))
    
    # Save task
    cache.save_task(
        task_id="task_123",
        title="Test Task",
        project_id="project_456"
    )
    
    # Retrieve task
    task_id = cache.get_task_id_by_title("Test Task")
    assert task_id == "task_123"
    
    # Check file exists and has correct content
    assert cache_file.exists()
    with open(cache_file, 'r') as f:
        data = json.load(f)
        assert "task_123" in data
        assert data["task_123"]["title"] == "Test Task"


def test_cache_get_task_case_insensitive(tmp_path):
    """Test that cache search is case-insensitive"""
    cache_file = tmp_path / "test_cache.json"
    cache = TaskCacheService(cache_file=str(cache_file))
    
    cache.save_task("task_123", "Test Task", "project_456")
    
    # Different case
    task_id = cache.get_task_id_by_title("test task")
    assert task_id == "task_123"
    
    task_id = cache.get_task_id_by_title("TEST TASK")
    assert task_id == "task_123"


def test_cache_get_nonexistent_task(tmp_path):
    """Test getting non-existent task returns None"""
    cache_file = tmp_path / "test_cache.json"
    cache = TaskCacheService(cache_file=str(cache_file))
    
    task_id = cache.get_task_id_by_title("Non-existent Task")
    assert task_id is None


def test_cache_delete_task(tmp_path):
    """Test deleting task from cache"""
    cache_file = tmp_path / "test_cache.json"
    cache = TaskCacheService(cache_file=str(cache_file))
    
    cache.save_task("task_123", "Test Task", "project_456")
    assert cache.get_task_id_by_title("Test Task") == "task_123"
    
    cache.delete_task("task_123")
    assert cache.get_task_id_by_title("Test Task") is None


def test_cache_load_existing(tmp_path):
    """Test loading existing cache file"""
    cache_file = tmp_path / "test_cache.json"
    
    # Create cache file manually
    with open(cache_file, 'w') as f:
        json.dump({
            "task_123": {
                "title": "Existing Task",
                "project_id": "project_456"
            }
        }, f)
    
    cache = TaskCacheService(cache_file=str(cache_file))
    task_id = cache.get_task_id_by_title("Existing Task")
    assert task_id == "task_123"


