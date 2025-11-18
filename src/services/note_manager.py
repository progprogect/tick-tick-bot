"""
Note management service
"""

from src.api.ticktick_client import TickTickClient
from src.models.command import ParsedCommand
from src.services.task_cache import TaskCacheService
from src.services.project_cache_service import ProjectCacheService
from src.services.task_search_service import TaskSearchService
from src.utils.logger import logger


class NoteManager:
    """Service for managing notes"""
    
    def __init__(self, ticktick_client: TickTickClient):
        """
        Initialize note manager
        
        Args:
            ticktick_client: TickTick API client
        """
        self.client = ticktick_client
        self.cache = TaskCacheService()
        self.project_cache = ProjectCacheService(ticktick_client)
        self.task_search = TaskSearchService(ticktick_client, self.cache, self.project_cache)
        self.logger = logger
    
    async def add_note(self, command: ParsedCommand) -> str:
        """
        Add note to task
        
        Args:
            command: Parsed command with task ID/title and notes
            
        Returns:
            Success message
        """
        try:
            if not command.task_id:
                if not command.title:
                    raise ValueError("Не указано название задачи или ID для добавления заметки")
                
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
            
            if not command.notes:
                raise ValueError("Заметка не указана")
            
            # Get current task data to merge notes
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
                                'notes': task_from_api.get('content', ''),
                                'tags': task_from_api.get('tags', []),
                            }
                    except Exception as e:
                        self.logger.warning(f"Could not get task from API: {e}")
                        raise ValueError(f"Задача {command.task_id} не найдена в кэше и не может быть получена из API")
                else:
                    raise ValueError(f"Задача {command.task_id} не найдена в кэше и project_id не указан для получения из API")
            
            # Merge existing notes with new notes
            existing_notes = original_task_data.get('notes', '')
            new_notes = command.notes
            if existing_notes:
                combined_notes = f"{existing_notes}\n\n{new_notes}"
            else:
                combined_notes = new_notes
            
            # Get task title for response (prioritize: found task > cache > command.title)
            task_title = command.title
            if not task_title:
                task_title = original_task_data.get('title', 'задача')
            if not task_title or task_title == 'задача':
                # Try to get from cache one more time
                task_data = self.cache.get_task_data(command.task_id)
                if task_data and task_data.get('title'):
                    task_title = task_data.get('title')
            
            # Update task with merged notes using correct API endpoint
            await self.client.update_task(
                task_id=command.task_id,
                notes=combined_notes,
            )
            
            # Update cache with new notes
            self.cache.update_task_field(command.task_id, 'notes', combined_notes)
            
            self.logger.info(f"Note added to task {command.task_id}")
            
            # Format detailed response
            note_preview = new_notes[:50] + "..." if len(new_notes) > 50 else new_notes
            had_existing_notes = bool(existing_notes)
            
            if had_existing_notes:
                return (
                    f"✓ Заметка добавлена к задаче '{task_title}'\n\n"
                    f"📝 Добавленный текст: {note_preview}\n"
                    f"ℹ️ Заметка добавлена к существующей заметке задачи"
                )
            else:
                return (
                    f"✓ Заметка добавлена к задаче '{task_title}'\n\n"
                    f"📝 Текст заметки: {note_preview}"
                )
            
        except ValueError:
            # Re-raise ValueError as-is (it's already user-friendly)
            raise
        except Exception as e:
            self.logger.error(f"Error adding note: {e}", exc_info=True)
            raise
