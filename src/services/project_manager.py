"""
Project management service
"""

from typing import Optional
from src.api.ticktick_client import TickTickClient
from src.models.command import ParsedCommand
from src.services.project_cache_service import ProjectCacheService
from src.utils.logger import logger
from src.utils.formatters import format_project_created


class ProjectManager:
    """Service for managing projects"""
    
    def __init__(self, ticktick_client: TickTickClient):
        """
        Initialize project manager
        
        Args:
            ticktick_client: TickTick API client
        """
        self.client = ticktick_client
        self.project_cache = ProjectCacheService(ticktick_client)
        self.logger = logger
    
    async def create_project(self, command: ParsedCommand) -> str:
        """
        Create a new project
        
        Args:
            command: ParsedCommand with project_name and optional parameters
            
        Returns:
            Formatted response message
        """
        # 1. Валидация: project_name обязателен
        if not command.project_name:
            raise ValueError("Название проекта обязательно для создания проекта")
        
        # 2. Вызов TickTickClient.create_project()
        try:
            project_data = await self.client.create_project(
                name=command.project_name,
                color=command.project_color,
                view_mode=command.project_view_mode,
                kind=command.project_kind,
                sort_order=None,  # API не требует sort_order при создании
            )
            
            self.logger.info(
                f"[ProjectManager] Project created: {project_data.get('id')} "
                f"('{project_data.get('name')}')"
            )
            
            # 3. Инвалидация кэша проектов после успешного создания
            self.project_cache.clear_cache()
            self.logger.debug("[ProjectManager] Projects cache cleared after creation")
            
            # 4. Форматирование ответа
            return format_project_created(project_data)
            
        except Exception as e:
            self.logger.error(f"[ProjectManager] Error creating project: {e}", exc_info=True)
            raise

