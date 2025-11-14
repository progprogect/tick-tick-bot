"""
Project management service
"""

from typing import Optional
from src.api.ticktick_client import TickTickClient
from src.models.command import ParsedCommand
from src.services.project_cache_service import ProjectCacheService
from src.utils.logger import logger
from src.utils.formatters import format_project_created, format_project_deleted


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
    
    async def delete_project(self, command: ParsedCommand) -> str:
        """
        Delete a project
        
        Args:
            command: ParsedCommand with project_id or project_name
            
        Returns:
            Formatted response message
        """
        # 1. Валидация: нужен либо project_id, либо project_name
        project_id = command.project_id
        project_name = command.project_name
        
        if not project_id and not project_name:
            raise ValueError("Необходимо указать ID проекта или название проекта для удаления")
        
        # 2. Если указано только название, найти project_id по названию
        if not project_id and project_name:
            projects = await self.client.get_projects()
            
            # Поиск проекта по названию (с учетом эмодзи)
            import re
            def clean_name(name: str) -> str:
                """Remove emojis and extra spaces from project name"""
                if not name:
                    return ""
                emoji_pattern = re.compile(
                    "["
                    "\U0001F600-\U0001F64F"  # emoticons
                    "\U0001F300-\U0001F5FF"  # symbols & pictographs
                    "\U0001F680-\U0001F6FF"  # transport & map symbols
                    "\U0001F1E0-\U0001F1FF"  # flags (iOS)
                    "\U00002702-\U000027B0"
                    "\U000024C2-\U0001F251"
                    "]+", flags=re.UNICODE
                )
                return emoji_pattern.sub('', name).strip().lower()
            
            cleaned_target_name = clean_name(project_name)
            found_project = None
            
            for project in projects:
                original_name = project.get("name", "")
                cleaned_project_name = clean_name(original_name)
                
                # Проверка точного совпадения или совпадения без учета регистра и эмодзи
                if (cleaned_target_name == cleaned_project_name or 
                    cleaned_target_name in cleaned_project_name or 
                    cleaned_project_name in cleaned_target_name):
                    found_project = project
                    break
            
            if not found_project:
                raise ValueError(f"Проект '{project_name}' не найден")
            
            project_id = found_project.get("id")
            project_name = found_project.get("name", project_name)
            self.logger.info(f"[ProjectManager] Found project by name: '{project_name}' (ID: {project_id})")
        elif project_id and not project_name:
            # Если указан только ID, получить название проекта для сообщения
            try:
                projects = await self.client.get_projects()
                found_project = next((p for p in projects if p.get("id") == project_id), None)
                if found_project:
                    project_name = found_project.get("name", "Проект")
                else:
                    project_name = "Проект"
            except Exception as e:
                self.logger.warning(f"[ProjectManager] Could not get project name: {e}")
                project_name = "Проект"
        
        # 3. Вызов TickTickClient.delete_project()
        try:
            await self.client.delete_project(project_id)
            
            self.logger.info(
                f"[ProjectManager] Project deleted: {project_id} ('{project_name}')"
            )
            
            # 4. Инвалидация кэша проектов после успешного удаления
            self.project_cache.clear_cache()
            self.logger.debug("[ProjectManager] Projects cache cleared after deletion")
            
            # 5. Форматирование ответа
            return format_project_deleted(project_name)
            
        except Exception as e:
            self.logger.error(f"[ProjectManager] Error deleting project: {e}", exc_info=True)
            raise

