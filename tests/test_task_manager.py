"""
Tests for task manager
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime
from src.models.command import ParsedCommand, ActionType, Recurrence
from src.services.task_manager import TaskManager
from src.services.recurring_task_manager import RecurringTaskManager


@pytest.mark.asyncio
async def test_create_task(mock_ticktick_client, task_cache_service):
    """Test creating a task"""
    manager = TaskManager(mock_ticktick_client)
    manager.cache = task_cache_service
    
    command = ParsedCommand(
        action=ActionType.CREATE_TASK,
        title="Test Task",
        project_id="inbox123"
    )
    
    result = await manager.create_task(command)
    
    # Check that task was created
    mock_ticktick_client.create_task.assert_called_once()
    assert "Test Task" in result or "создана" in result
    
    # Check that task was cached
    task_id = manager.cache.get_task_id_by_title("Test Task")
    assert task_id == "test_task_id_123"


@pytest.mark.asyncio
async def test_update_task_with_cache(mock_ticktick_client, task_cache_service):
    """Test updating task using cache"""
    manager = TaskManager(mock_ticktick_client)
    manager.cache = task_cache_service
    
    # First, save task to cache
    manager.cache.save_task("test_task_id_123", "Test Task", "inbox123")
    
    command = ParsedCommand(
        action=ActionType.UPDATE_TASK,
        title="Test Task",
        due_date="2024-11-05T00:00:00+00:00"
    )
    
    result = await manager.update_task(command)
    
    # Check that update was called with correct task_id
    mock_ticktick_client.update_task.assert_called_once()
    call_args = mock_ticktick_client.update_task.call_args
    assert call_args[1]["task_id"] == "test_task_id_123"
    assert "dueDate" in call_args[1] or "due_date" in str(call_args)


@pytest.mark.asyncio
async def test_update_task_without_cache_fails(mock_ticktick_client, task_cache_service):
    """Test updating task that doesn't exist in cache"""
    manager = TaskManager(mock_ticktick_client)
    manager.cache = task_cache_service
    
    command = ParsedCommand(
        action=ActionType.UPDATE_TASK,
        title="Non-existent Task",
        due_date="2024-11-05T00:00:00+00:00"
    )
    
    # Should raise ValueError because task not found
    with pytest.raises(ValueError, match="не найдена"):
        await manager.update_task(command)


@pytest.mark.asyncio
async def test_delete_task_with_cache(mock_ticktick_client, task_cache_service):
    """Test deleting task using cache"""
    manager = TaskManager(mock_ticktick_client)
    manager.cache = task_cache_service
    
    # First, save task to cache
    manager.cache.save_task("test_task_id_123", "Test Task", "inbox123")
    
    command = ParsedCommand(
        action=ActionType.DELETE_TASK,
        title="Test Task"
    )
    
    result = await manager.delete_task(command)
    
    # Check that delete was called with task_id and project_id
    mock_ticktick_client.delete_task.assert_called_once_with("test_task_id_123", project_id="inbox123")
    
    # Check that task was removed from cache
    assert manager.cache.get_task_id_by_title("Test Task") is None


@pytest.mark.asyncio
async def test_delete_task_without_cache_fails(mock_ticktick_client, task_cache_service):
    """Test deleting task that doesn't exist in cache"""
    manager = TaskManager(mock_ticktick_client)
    manager.cache = task_cache_service
    
    command = ParsedCommand(
        action=ActionType.DELETE_TASK,
        title="Non-existent Task"
    )
    
    # Should raise ValueError because task not found
    with pytest.raises(ValueError, match="не найдена"):
        await manager.delete_task(command)


@pytest.mark.asyncio
async def test_update_task_with_recurrence(mock_ticktick_client, task_cache_service):
    """Test updating task with recurrence (adding repeatFlag)"""
    from src.services.task_search_service import TaskSearchService
    from src.services.project_cache_service import ProjectCacheService
    
    manager = TaskManager(mock_ticktick_client)
    manager.cache = task_cache_service
    manager.project_cache = MagicMock(spec=ProjectCacheService)
    manager.task_search = MagicMock(spec=TaskSearchService)
    
    # Mock task search to return existing task
    manager.task_search.find_task_by_title = AsyncMock(return_value={
        "id": "test_task_id_123",
        "title": "Test Task",
        "projectId": "inbox123"
    })
    
    # Save task to cache
    manager.cache.save_task("test_task_id_123", "Test Task", "inbox123")
    
    # Create command with recurrence
    command = ParsedCommand(
        action=ActionType.UPDATE_TASK,
        title="Test Task",
        recurrence=Recurrence(type="daily", interval=1)
    )
    
    result = await manager.update_task(command)
    
    # Check that update was called
    mock_ticktick_client.update_task.assert_called_once()
    call_args = mock_ticktick_client.update_task.call_args
    
    # Check that repeat_flag was passed
    assert call_args[1]["repeat_flag"] == "RRULE:FREQ=DAILY;INTERVAL=1"
    
    # Check that startDate was passed (through kwargs)
    # startDate should be in kwargs (update_data)
    kwargs = call_args[1]
    assert "startDate" in kwargs or any("startDate" in str(v) for v in kwargs.values())
    
    # Check that cache was updated with repeat_flag
    task_info = manager.cache.get_task_data("test_task_id_123")
    assert task_info is not None
    assert task_info.get("repeat_flag") == "RRULE:FREQ=DAILY;INTERVAL=1"


def test_recurring_task_manager_build_repeat_flag():
    """Test RecurringTaskManager._build_repeat_flag()"""
    # Test daily
    recurrence = Recurrence(type="daily", interval=1)
    repeat_flag = RecurringTaskManager._build_repeat_flag(recurrence)
    assert repeat_flag == "RRULE:FREQ=DAILY;INTERVAL=1"
    
    # Test weekly
    recurrence = Recurrence(type="weekly", interval=1)
    repeat_flag = RecurringTaskManager._build_repeat_flag(recurrence)
    assert repeat_flag == "RRULE:FREQ=WEEKLY;INTERVAL=1"
    
    # Test monthly
    recurrence = Recurrence(type="monthly", interval=1)
    repeat_flag = RecurringTaskManager._build_repeat_flag(recurrence)
    assert repeat_flag == "RRULE:FREQ=MONTHLY;INTERVAL=1"
    
    # Test with custom interval
    recurrence = Recurrence(type="daily", interval=2)
    repeat_flag = RecurringTaskManager._build_repeat_flag(recurrence)
    assert repeat_flag == "RRULE:FREQ=DAILY;INTERVAL=2"


def test_recurring_task_manager_determine_start_date():
    """Test RecurringTaskManager._determine_start_date()"""
    # Test with due_date
    due_date = "2024-11-05T10:00:00+03:00"
    start_date = RecurringTaskManager._determine_start_date(due_date)
    assert start_date is not None
    assert "2024-11-05" in start_date
    assert "+0000" in start_date
    
    # Test without due_date (should use current date)
    start_date = RecurringTaskManager._determine_start_date()
    assert start_date is not None
    assert "+0000" in start_date
    # Should be in format yyyy-MM-dd'T'HH:mm:ss+0000
    assert "T" in start_date
    assert len(start_date) > 15  # At least date and time

