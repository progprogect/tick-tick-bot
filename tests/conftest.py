"""
Pytest configuration and fixtures
"""

import pytest
import os
from unittest.mock import AsyncMock, MagicMock
from src.api.ticktick_client import TickTickClient
from src.api.openai_client import OpenAIClient
from src.services.task_manager import TaskManager
from src.services.task_cache import TaskCacheService
from src.services.gpt_service import GPTService


@pytest.fixture
def mock_ticktick_client():
    """Mock TickTick client"""
    client = MagicMock(spec=TickTickClient)
    client.access_token = "test_token"
    client.authenticate = AsyncMock(return_value=True)
    client.create_task = AsyncMock(return_value={
        "id": "test_task_id_123",
        "title": "Test Task",
        "projectId": "inbox123",
        "status": 0
    })
    client.update_task = AsyncMock(return_value={
        "id": "test_task_id_123",
        "title": "Updated Task",
        "projectId": "inbox123",
        "status": 0
    })
    client.delete_task = AsyncMock(return_value=True)
    client.get_tasks = AsyncMock(return_value=[])
    client.add_tags = AsyncMock(return_value={
        "id": "test_task_id_123",
        "tags": ["important"]
    })
    return client


@pytest.fixture
def mock_openai_client():
    """Mock OpenAI client"""
    client = MagicMock(spec=OpenAIClient)
    client.parse_command = AsyncMock(return_value={
        "action": "create_task",
        "title": "Test Task"
    })
    client.transcribe_audio = AsyncMock(return_value="create task test")
    return client


@pytest.fixture
def mock_gpt_service(mock_openai_client):
    """Mock GPT service"""
    service = MagicMock(spec=GPTService)
    service.parse_command = AsyncMock(return_value=MagicMock(
        action="create_task",
        title="Test Task",
        task_id=None,
        project_id=None,
        due_date=None,
        priority=None,
        tags=None,
        notes=None
    ))
    return service


@pytest.fixture
def task_cache_service(tmp_path):
    """Task cache service with temporary file"""
    cache_file = tmp_path / "test_task_cache.json"
    service = TaskCacheService(cache_file=str(cache_file))
    return service


@pytest.fixture
def task_manager(mock_ticktick_client, task_cache_service):
    """Task manager with mocked dependencies"""
    manager = TaskManager(mock_ticktick_client)
    manager.cache = task_cache_service
    return manager


