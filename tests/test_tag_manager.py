"""
Tests for tag manager - testing real errors
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from src.models.command import ParsedCommand, ActionType
from src.services.tag_manager import TagManager
from src.services.task_cache import TaskCacheService


@pytest.mark.asyncio
async def test_add_tags_with_cache(mock_ticktick_client, task_cache_service):
    """Test adding tags using cache - REAL ERROR: TagManager doesn't use cache"""
    manager = TagManager(mock_ticktick_client)
    manager.cache = task_cache_service
    
    # Save task to cache first (with existing tags for testing merge)
    task_cache_service.save_task("test_task_id_123", "Test Task", "inbox123", status="active")
    # Manually add existing tags to cache for testing merge
    task_data = task_cache_service.get_task_data("test_task_id_123")
    if task_data:
        task_data['tags'] = ['existing_tag']
        task_cache_service._cache["test_task_id_123"] = task_data
        task_cache_service._save_cache()
    
    command = ParsedCommand(
        action=ActionType.ADD_TAGS,
        title="Test Task",
        tags=["important", "urgent"]
    )
    
    result = await manager.add_tags(command)
    
    # Check that task was found via cache
    assert command.task_id == "test_task_id_123"
    
    # Check that update_task was called (add_tags now uses update_task directly)
    # TagManager gets task data from cache and merges tags
    mock_ticktick_client.update_task.assert_called_once()
    call_args = mock_ticktick_client.update_task.call_args
    assert call_args[1]["task_id"] == "test_task_id_123"
    assert "tags" in call_args[1]
    # Tags should be merged (existing + new)
    merged_tags = call_args[1]["tags"]
    # Should contain both existing and new tags
    assert "existing_tag" in merged_tags
    assert "important" in merged_tags
    assert "urgent" in merged_tags
    
    assert "добавлены" in result.lower()


@pytest.mark.asyncio
async def test_add_tags_without_cache_fails(mock_ticktick_client, task_cache_service):
    """Test adding tags when task not in cache - should fail gracefully"""
    manager = TagManager(mock_ticktick_client)
    manager.cache = task_cache_service
    
    # Mock get_tasks to return empty (simulating API failure)
    mock_ticktick_client.get_tasks = AsyncMock(return_value=[])
    
    command = ParsedCommand(
        action=ActionType.ADD_TAGS,
        title="Non-existent Task",
        tags=["important"]
    )
    
    # Should raise ValueError
    with pytest.raises(ValueError, match="не найдена"):
        await manager.add_tags(command)

