"""
Reminder management service
"""

from src.api.ticktick_client import TickTickClient
from src.models.command import ParsedCommand
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
            from src.services.task_cache import TaskCacheService
            cache = TaskCacheService()
            
            if not command.task_id:
                # Try to find task by title using cache
                task_id = cache.get_task_id_by_title(command.title)
                if not task_id:
                    # Fallback to API search
                    tasks = await self.client.get_tasks()
                    matching_task = next(
                        (t for t in tasks if t.get("title") == command.title),
                        None
                    )
                    
                    if not matching_task:
                        raise ValueError(f"Задача '{command.title}' не найдена")
                    
                    task_id = matching_task.get("id")
                    title = matching_task.get("title", "Задача")
                else:
                    task_data = cache.get_task_data(task_id)
                    title = task_data.get("title", "Задача") if task_data else command.title
                
                command.task_id = task_id
            else:
                # Get task title from cache
                task_data = cache.get_task_data(command.task_id)
                title = task_data.get("title", "Задача") if task_data else "Задача"
            
            if not command.reminder:
                raise ValueError("Время напоминания не указано")
            
            # Convert reminder time to TRIGGER format
            trigger = self.client._convert_reminder_time_to_trigger(command.reminder)
            
            # Get existing reminders from cache if available
            existing_reminders = []
            task_data = cache.get_task_data(command.task_id)
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
            cache.update_task_field(command.task_id, "reminders", reminders)
            
            self.logger.info(f"Reminder set for task {command.task_id} at {command.reminder} (trigger: {trigger})")
            
            # Format reminder time for display
            from datetime import datetime
            try:
                reminder_dt = datetime.fromisoformat(command.reminder.replace('Z', '+00:00'))
                reminder_text = reminder_dt.strftime("%d.%m.%Y %H:%M")
            except:
                reminder_text = command.reminder
            
            return f"✓ Напоминание установлено для задачи '{title}' на {reminder_text}"
            
        except Exception as e:
            self.logger.error(f"Error setting reminder: {e}", exc_info=True)
            raise


