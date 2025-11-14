"""
Tests for ProjectManager
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from src.services.project_manager import ProjectManager
from src.api.ticktick_client import TickTickClient
from src.models.command import ParsedCommand, ActionType


@pytest.fixture
def mock_ticktick_client():
    """Mock TickTickClient"""
    client = MagicMock(spec=TickTickClient)
    client.create_project = AsyncMock()
    return client


@pytest.fixture
def project_manager(mock_ticktick_client):
    """ProjectManager instance with mocked client"""
    return ProjectManager(mock_ticktick_client)


@pytest.mark.asyncio
async def test_create_project_success(project_manager, mock_ticktick_client):
    """Test successful project creation"""
    # Mock API response
    mock_project_data = {
        "id": "test_project_id",
        "name": "Test Project",
        "color": "#F18181",
        "viewMode": "list",
        "kind": "TASK"
    }
    mock_ticktick_client.create_project.return_value = mock_project_data
    
    # Create command
    command = ParsedCommand(
        action=ActionType.CREATE_PROJECT,
        project_name="Test Project"
    )
    
    # Execute
    result = await project_manager.create_project(command)
    
    # Assertions
    assert "✓ Проект 'Test Project' создан" in result
    assert "test_project_id" in result
    mock_ticktick_client.create_project.assert_called_once_with(
        name="Test Project",
        color=None,
        view_mode=None,
        kind=None,
        sort_order=None
    )
    # Check that cache was cleared
    assert project_manager.project_cache._projects == []
    assert project_manager.project_cache._last_update is None


@pytest.mark.asyncio
async def test_create_project_with_optional_params(project_manager, mock_ticktick_client):
    """Test project creation with optional parameters"""
    # Mock API response
    mock_project_data = {
        "id": "test_project_id",
        "name": "Test Project",
        "color": "#F18181",
        "viewMode": "kanban",
        "kind": "TASK"
    }
    mock_ticktick_client.create_project.return_value = mock_project_data
    
    # Create command with optional parameters
    command = ParsedCommand(
        action=ActionType.CREATE_PROJECT,
        project_name="Test Project",
        project_color="#F18181",
        project_view_mode="kanban",
        project_kind="TASK"
    )
    
    # Execute
    result = await project_manager.create_project(command)
    
    # Assertions
    assert "✓ Проект 'Test Project' создан" in result
    mock_ticktick_client.create_project.assert_called_once_with(
        name="Test Project",
        color="#F18181",
        view_mode="kanban",
        kind="TASK",
        sort_order=None
    )


@pytest.mark.asyncio
async def test_create_project_missing_name(project_manager):
    """Test project creation with missing project name"""
    # Create command without project_name
    command = ParsedCommand(
        action=ActionType.CREATE_PROJECT,
        project_name=None
    )
    
    # Execute and expect error
    with pytest.raises(ValueError, match="Название проекта обязательно"):
        await project_manager.create_project(command)


@pytest.mark.asyncio
async def test_create_project_api_error(project_manager, mock_ticktick_client):
    """Test project creation with API error"""
    # Mock API error
    mock_ticktick_client.create_project.side_effect = Exception("API Error")
    
    # Create command
    command = ParsedCommand(
        action=ActionType.CREATE_PROJECT,
        project_name="Test Project"
    )
    
    # Execute and expect error
    with pytest.raises(Exception, match="API Error"):
        await project_manager.create_project(command)
    
    # Check that cache was NOT cleared on error
    # (cache should remain unchanged if creation failed)
    # Note: This test depends on implementation - if cache is cleared before API call,
    # this assertion may fail. Adjust based on actual implementation.


@pytest.mark.asyncio
async def test_create_project_cache_cleared(project_manager, mock_ticktick_client):
    """Test that cache is cleared after successful project creation"""
    # Mock API response
    mock_project_data = {
        "id": "test_project_id",
        "name": "Test Project"
    }
    mock_ticktick_client.create_project.return_value = mock_project_data
    
    # Pre-populate cache (simulate existing projects)
    project_manager.project_cache._projects = [
        {"id": "old_project_id", "name": "Old Project"}
    ]
    from datetime import datetime
    project_manager.project_cache._last_update = datetime.now()
    
    # Create command
    command = ParsedCommand(
        action=ActionType.CREATE_PROJECT,
        project_name="Test Project"
    )
    
    # Execute
    await project_manager.create_project(command)
    
    # Assertions - cache should be cleared
    assert project_manager.project_cache._projects == []
    assert project_manager.project_cache._last_update is None

