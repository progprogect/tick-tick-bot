"""
Tag management service
"""

from typing import List, Dict, Any
from src.api.ticktick_client import TickTickClient
from src.models.command import ParsedCommand
from src.services.task_cache import TaskCacheService
from src.services.project_cache_service import ProjectCacheService
from src.services.task_search_service import TaskSearchService
from src.utils.logger import logger


class TagManager:
    """Service for managing tags"""
    
    def __init__(self, ticktick_client: TickTickClient):
        """
        Initialize tag manager
        
        Args:
            ticktick_client: TickTick API client
        """
        self.client = ticktick_client
        self.cache = TaskCacheService()
        self.project_cache = ProjectCacheService(ticktick_client)
        self.task_search = TaskSearchService(ticktick_client, self.cache, self.project_cache)
        self.logger = logger
    
    async def add_tags(self, command: ParsedCommand) -> str:
        """
        Add tags to task
        
        Args:
            command: Parsed command with task ID/title and tags
            
        Returns:
            Success message
        """
        try:
            if not command.task_id:
                if not command.title:
                    raise ValueError("Не указано название задачи или ID для добавления тегов")
                
                # Use TaskSearchService to find task
                task = await self.task_search.find_task_by_title(
                    title=command.title,
                    project_id=command.project_id,
                )
                
                if task:
                    command.task_id = task.get("id")
                    self.logger.debug(f"Found task ID: {command.task_id}")
                else:
                    raise ValueError(
                        f"Задача '{command.title}' не найдена. "
                        f"Попробуйте создать новую задачу или укажите ID задачи."
                    )
            
            if not command.tags:
                raise ValueError("Теги не указаны")
            
            # Get current task data to merge tags
            original_task_data = self.cache.get_task_data(command.task_id)
            if not original_task_data:
                raise ValueError(f"Задача {command.task_id} не найдена в кэше")
            
            # Merge existing tags with new tags
            existing_tags = original_task_data.get('tags', [])
            if not isinstance(existing_tags, list):
                existing_tags = []
            merged_tags = list(set(existing_tags + command.tags))  # Remove duplicates
            
            # Update task with merged tags using correct API endpoint
            await self.client.update_task(
                task_id=command.task_id,
                tags=merged_tags,
            )
            
            # Update cache with new tags
            self.cache.update_task_field(command.task_id, 'tags', merged_tags)
            
            self.logger.info(f"Tags added to task {command.task_id}: {command.tags}")
            return f"✓ Теги добавлены к задаче: {', '.join(command.tags)}"
            
        except ValueError:
            # Re-raise ValueError as-is (it's already user-friendly)
            raise
        except Exception as e:
            self.logger.error(f"Error adding tags: {e}", exc_info=True)
            raise
    
    
    async def bulk_add_tags_with_urgency(
        self,
        project_id: str,
        urgency_map: Dict[str, str],
    ) -> str:
        """
        Add urgency tags to multiple tasks
        
        Args:
            project_id: Project/list ID
            urgency_map: Dictionary mapping task IDs to urgency levels
            
        Returns:
            Success message with count
        """
        try:
            # Get tasks from project
            tasks = await self.client.get_tasks(project_id=project_id)
            
            if not tasks:
                return "В списке задач не найдено"
            
            # Map urgency levels to tags
            urgency_to_tag = {
                "urgent": "срочно",
                "medium": "средне",
                "low": "низкий",
            }
            
            processed = 0
            
            for task in tasks:
                task_id = task.get("id")
                if task_id in urgency_map:
                    urgency = urgency_map[task_id]
                    tag = urgency_to_tag.get(urgency, "средне")
                    
                    try:
                        await self.client.add_tags(task_id, [tag])
                        processed += 1
                    except Exception as e:
                        self.logger.error(f"Error adding tag to task {task_id}: {e}")
            
            # Count by urgency
            urgent_count = sum(1 for u in urgency_map.values() if u == "urgent")
            medium_count = sum(1 for u in urgency_map.values() if u == "medium")
            low_count = sum(1 for u in urgency_map.values() if u == "low")
            
            message = (
                f"✓ Добавлены теги срочности к {processed} задачам: "
                f"{urgent_count} высокий, {medium_count} средний, {low_count} низкий"
            )
            
            return message
            
        except Exception as e:
            self.logger.error(f"Error in bulk add tags: {e}", exc_info=True)
            raise
