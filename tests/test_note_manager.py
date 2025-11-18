"""
Tests for note manager - testing real errors
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from src.models.command import ParsedCommand, ActionType
from src.services.note_manager import NoteManager
from src.services.task_cache import TaskCacheService


@pytest.mark.asyncio
async def test_add_note_with_cache(mock_ticktick_client, task_cache_service):
    """Test adding note using cache - REAL ERROR: NoteManager doesn't use cache"""
    manager = NoteManager(mock_ticktick_client)
    manager.cache = task_cache_service
    
    # Save task to cache first
    task_cache_service.save_task("test_task_id_123", "Test Task", "inbox123")
    
    command = ParsedCommand(
        action=ActionType.ADD_NOTE,
        title="Test Task",
        notes="This is a test note"
    )
    
    result = await manager.add_note(command)
    
    # Check that task was found via cache
    assert command.task_id == "test_task_id_123"
    
    # Check that update_task was called with notes
    mock_ticktick_client.update_task.assert_called_once()
    call_args = mock_ticktick_client.update_task.call_args
    assert call_args[1]["task_id"] == "test_task_id_123"
    assert call_args[1]["notes"] == "This is a test note"
    
    assert "добавлена" in result.lower()


