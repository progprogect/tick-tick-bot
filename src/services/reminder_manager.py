"""
Reminder management service
"""

from src.api.ticktick_client import TickTickClient
from src.models.command import ParsedCommand
from src.services.task_cache import TaskCacheService
from src.services.project_cache_service import ProjectCacheService
from src.services.task_search_service import TaskSearchService
from src.utils.logger import logger


class ReminderManager:
    """Service for managing reminders"""
    
    def __init__(self, ticktick_client: TickTickClient):
        """
        Initialize reminder manager
        
        Args:
            ticktick_client: TickTick API client
        """
        self.client = ticktick_client
        self.cache = TaskCacheService()
        self.project_cache = ProjectCacheService(ticktick_client)
        self.task_search = TaskSearchService(ticktick_client, self.cache, self.project_cache)
        self.logger = logger
    
    async def set_reminder(self, command: ParsedCommand) -> str:
        """
        Set reminder for task
        
        According to TickTick API documentation:
        - Use reminders array in task update (e.g., ["TRIGGER:P0DT9H0M0S", "TRIGGER:PT0S"])
        - Reminders are set via update_task with reminders field
        
        Args:
            command: Parsed command with task ID/title and reminder time
            
        Returns:
            Success message
        """
        try:
            if not command.task_id:
                if not command.title:
                    raise ValueError("Не указано название задачи или ID для установки напоминания")
                
                # Use TaskSearchService to find task
                task = await self.task_search.find_task_by_title(
                    title=command.title,
                    project_id=command.project_id,
                )
                
                if task:
                    command.task_id = task.get("id")
                    title = task.get("title", command.title)
                    self.logger.debug(f"Found task ID: {command.task_id}")
                else:
                    raise ValueError(f"Задача '{command.title}' не найдена")
            else:
                # Get task title from cache
                task_data = self.cache.get_task_data(command.task_id)
                title = task_data.get("title", "Задача") if task_data else "Задача"
            
            if not command.reminder:
                raise ValueError("Время напоминания не указано")
            
            # Convert reminder time to TRIGGER format
            trigger = self.client._convert_reminder_time_to_trigger(command.reminder)
            
            # Get existing reminders from cache if available
            existing_reminders = []
            task_data = self.cache.get_task_data(command.task_id)
            if task_data and task_data.get("reminders"):
                existing_reminders = task_data.get("reminders", [])
                if not isinstance(existing_reminders, list):
                    existing_reminders = []
            
            # Add new reminder to existing ones
            reminders = existing_reminders.copy()
            if trigger not in reminders:
                reminders.append(trigger)
            
            # Update task with reminders
            await self.client.update_task(
                task_id=command.task_id,
                reminders=reminders,
            )
            
            # Update cache with reminders
            self.cache.update_task_field(command.task_id, "reminders", reminders)
            
            self.logger.info(f"Reminder set for task {command.task_id} at {command.reminder} (trigger: {trigger})")
            
            # Format reminder time for display
            from datetime import datetime
            try:
                reminder_dt = datetime.fromisoformat(command.reminder.replace('Z', '+00:00'))
                reminder_text = reminder_dt.strftime("%d.%m.%Y %H:%M")
            except:
                reminder_text = command.reminder
            
            # Check if there were existing reminders
            had_existing_reminders = len(existing_reminders) > 0
            
            if had_existing_reminders:
                return (
                    f"✓ Напоминание добавлено к задаче '{title}'\n\n"
                    f"⏰ Новое напоминание: {reminder_text}\n"
                    f"ℹ️ Напоминание добавлено к существующим напоминаниям задачи"
                )
            else:
                return (
                    f"✓ Напоминание установлено для задачи '{title}'\n\n"
                    f"⏰ Время напоминания: {reminder_text}"
                )
            
        except Exception as e:
            self.logger.error(f"Error setting reminder: {e}", exc_info=True)
            raise


