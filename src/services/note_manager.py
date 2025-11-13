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
                    self.logger.debug(f"Found task ID: {command.task_id}")
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
                raise ValueError(f"Задача {command.task_id} не найдена в кэше")
            
            # Merge existing notes with new notes
            existing_notes = original_task_data.get('notes', '')
            new_notes = command.notes
            if existing_notes:
                combined_notes = f"{existing_notes}\n\n{new_notes}"
            else:
                combined_notes = new_notes
            
            # Update task with merged notes using correct API endpoint
            await self.client.update_task(
                task_id=command.task_id,
                notes=combined_notes,
            )
            
            # Update cache with new notes
            self.cache.update_task_field(command.task_id, 'notes', combined_notes)
            
            self.logger.info(f"Note added to task {command.task_id}")
            return f"✓ Заметка добавлена к задаче '{command.title or 'задача'}'"
            
        except ValueError:
            # Re-raise ValueError as-is (it's already user-friendly)
            raise
        except Exception as e:
            self.logger.error(f"Error adding note: {e}", exc_info=True)
            raise
