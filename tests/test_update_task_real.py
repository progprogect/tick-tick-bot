"""
Real test for update_task - checking actual error scenarios
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from src.models.command import ParsedCommand, ActionType
from src.services.task_manager import TaskManager
from src.services.task_cache import TaskCacheService


@pytest.mark.asyncio
async def test_update_task_with_only_due_date(mock_ticktick_client, task_cache_service):
    """Test updating task with only due_date - REAL ERROR: update_data might be empty"""
    manager = TaskManager(mock_ticktick_client)
    manager.cache = task_cache_service
    
    # Save task to cache first
    task_cache_service.save_task("test_task_id_123", "Test Task", "inbox123")
    
    command = ParsedCommand(
        action=ActionType.UPDATE_TASK,
        title="Test Task",  # Used for finding
        due_date="2024-11-05T00:00:00+00:00"  # What we want to update
    )
    
    # This should work - we find task by title, then update due_date
    result = await manager.update_task(command)
    
    # Check that task was found
    assert command.task_id == "test_task_id_123"
    
    # Check that update was called with dueDate
    mock_ticktick_client.update_task.assert_called_once()
    call_kwargs = mock_ticktick_client.update_task.call_args[1]
    assert "dueDate" in call_kwargs or "due_date" in str(call_kwargs)
    
    # Should not raise error about "no fields to update"


@pytest.mark.asyncio
async def test_update_task_empty_update_data_error(mock_ticktick_client, task_cache_service):
    """Test that update fails when no fields to update - REAL ERROR check"""
    manager = TaskManager(mock_ticktick_client)
    manager.cache = task_cache_service
    
    task_cache_service.save_task("test_task_id_123", "Test Task", "inbox123")
    
    # Command with only title (for finding), no update fields
    command = ParsedCommand(
        action=ActionType.UPDATE_TASK,
        title="Test Task",
        # No due_date, no project_id, no priority, no tags, no notes
    )
    
    # This should raise ValueError because no fields to update
    with pytest.raises(ValueError, match="Не указаны параметры"):
        await manager.update_task(command)


