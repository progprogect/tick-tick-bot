"""
Tests for GPT service
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from src.services.gpt_service import GPTService
from src.services.prompt_manager import PromptManager


@pytest.mark.asyncio
async def test_parse_command_create_task(mock_openai_client):
    """Test parsing create task command"""
    from unittest.mock import patch
    
    service = GPTService()
    
    # Mock the openai_client
    with patch.object(service, 'openai_client', mock_openai_client):
        mock_openai_client.parse_command.return_value = {
            "action": "create_task",
            "title": "Buy milk",
            "project_id": None,
            "due_date": None,
            "priority": 0
        }
        
        result = await service.parse_command("Создай задачу купить молоко")
        
        assert result.action == "create_task"
        assert result.title == "Buy milk"
        mock_openai_client.parse_command.assert_called_once()


@pytest.mark.asyncio
async def test_parse_command_update_task(mock_openai_client):
    """Test parsing update task command"""
    from unittest.mock import patch
    
    service = GPTService()
    
    # Mock the openai_client
    with patch.object(service, 'openai_client', mock_openai_client):
        mock_openai_client.parse_command.return_value = {
            "action": "update_task",
            "title": "Buy milk",
            "due_date": "2024-11-05T00:00:00+00:00"
        }
        
        result = await service.parse_command("Измени задачу купить молоко на завтра")
        
        assert result.action == "update_task"
        assert result.title == "Buy milk"
        assert result.due_date is not None

