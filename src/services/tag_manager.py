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
                    # Save actual title and project_id from found task
                    if task.get("title"):
                        command.title = task.get("title")
                    if task.get("projectId") and not command.project_id:
                        command.project_id = task.get("projectId")
                    self.logger.debug(f"Found task ID: {command.task_id}, title: {command.title}, project_id: {command.project_id}")
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
                # Try to get from API if not in cache
                # Get project_id if not set
                project_id_for_api = command.project_id
                if not project_id_for_api:
                    # Try to get from cache
                    cached_task = self.cache.get_task_data(command.task_id)
                    if cached_task and cached_task.get('project_id'):
                        project_id_for_api = cached_task.get('project_id')
                
                if project_id_for_api:
                    try:
                        task_from_api = await self.client.get(
                            endpoint=f"/open/v1/project/{project_id_for_api}/task/{command.task_id}",
                            headers=self.client._get_headers(),
                        )
                        if isinstance(task_from_api, dict):
                            # Update cache with task data
                            self.cache.save_task(
                                task_id=command.task_id,
                                title=task_from_api.get('title', command.title or 'задача'),
                                project_id=project_id_for_api,
                            )
                            original_task_data = {
                                'title': task_from_api.get('title', command.title or 'задача'),
                                'tags': task_from_api.get('tags', []),
                                'notes': task_from_api.get('content', ''),
                            }
                    except Exception as e:
                        self.logger.warning(f"Could not get task from API: {e}")
                        raise ValueError(f"Задача {command.task_id} не найдена в кэше и не может быть получена из API")
                else:
                    raise ValueError(f"Задача {command.task_id} не найдена в кэше и project_id не указан для получения из API")
            
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
            
            # Get task title for response (prioritize: found task > cache > command.title)
            task_title = command.title
            if not task_title:
                task_title = original_task_data.get('title', 'задача')
            if not task_title or task_title == 'задача':
                # Try to get from cache one more time
                task_data = self.cache.get_task_data(command.task_id)
                if task_data and task_data.get('title'):
                    task_title = task_data.get('title')
            
            # Update cache with new tags
            self.cache.update_task_field(command.task_id, 'tags', merged_tags)
            
            self.logger.info(f"Tags added to task {command.task_id}: {command.tags}")
            
            # Format detailed response
            new_tags_list = ', '.join(command.tags)
            had_existing_tags = bool(existing_tags)
            
            if had_existing_tags:
                all_tags_list = ', '.join(merged_tags)
                return (
                    f"✓ Теги добавлены к задаче '{task_title}'\n\n"
                    f"🏷️ Новые теги: {new_tags_list}\n"
                    f"📋 Все теги задачи: {all_tags_list}"
                )
            else:
                return (
                    f"✓ Теги добавлены к задаче '{task_title}'\n\n"
                    f"🏷️ Добавленные теги: {new_tags_list}"
                )
            
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
