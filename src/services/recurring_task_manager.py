"""
Recurring task management service
"""

from typing import Optional
from src.api.ticktick_client import TickTickClient
from src.models.command import ParsedCommand
from src.utils.logger import logger


class RecurringTaskManager:
    """Service for managing recurring tasks"""
    
    def __init__(self, ticktick_client: TickTickClient):
        """
        Initialize recurring task manager
        
        Args:
            ticktick_client: TickTick API client
        """
        self.client = ticktick_client
        self.logger = logger
    
    async def create_recurring_task(self, command: ParsedCommand) -> str:
        """
        Create recurring task
        
        According to TickTick API documentation:
        - Use repeatFlag field with RRULE format (e.g., "RRULE:FREQ=DAILY;INTERVAL=1")
        
        Args:
            command: Parsed command with task details and recurrence
            
        Returns:
            Success message
        """
        try:
            if not command.title:
                raise ValueError("Название задачи не указано")
            
            if not command.recurrence:
                raise ValueError("Параметры повторения не указаны")
            
            # Map recurrence type to TickTick RRULE format
            recurrence_type = command.recurrence.type.upper()  # DAILY, WEEKLY, MONTHLY
            interval = command.recurrence.interval or 1
            
            # Build RRULE according to RFC 5545
            # Format: "RRULE:FREQ=DAILY;INTERVAL=1"
            repeat_flag = f"RRULE:FREQ={recurrence_type};INTERVAL={interval}"
            
            # IMPORTANT: TickTick API requires startDate for recurring tasks
            # If due_date is provided, use it as startDate
            # If not, use current date as startDate
            from datetime import datetime
            if command.due_date:
                # Parse due_date and use it as startDate
                try:
                    from datetime import datetime
                    due_dt = datetime.fromisoformat(command.due_date.replace('Z', '+00:00'))
                    start_date = due_dt.isoformat().replace('+00:00', '+0000')
                except:
                    # If parsing fails, use current date
                    start_date = datetime.now().strftime('%Y-%m-%dT%H:%M:%S+0000')
            else:
                # Use current date as startDate
                start_date = datetime.now().strftime('%Y-%m-%dT%H:%M:%S+0000')
            
            # Create task with repeatFlag and startDate
            # Note: repeatFlag requires startDate to work in TickTick API
            task_data = await self.client.create_task(
                title=command.title,
                project_id=command.project_id,
                due_date=command.due_date or start_date,
                priority=command.priority or 0,
                tags=command.tags or [],
                notes=command.notes,
                repeat_flag=repeat_flag,
                start_date=start_date,  # Required for recurring tasks
            )
            
            task_id = task_data.get('id')
            self.logger.info(f"Recurring task created: {task_id} with repeatFlag={repeat_flag}")
            
            # Save to cache with repeat_flag
            if task_id:
                from src.services.task_cache import TaskCacheService
                cache = TaskCacheService()
                cache.save_task(
                    task_id=task_id,
                    title=command.title,
                    project_id=command.project_id or task_data.get('projectId'),
                    tags=command.tags or [],
                    notes=command.notes,
                    repeat_flag=repeat_flag,
                )
            
            recurrence_text = self._format_recurrence(command.recurrence.type, interval)
            return f"✓ Создана повторяющаяся задача '{command.title}' ({recurrence_text})"
            
        except Exception as e:
            self.logger.error(f"Error creating recurring task: {e}", exc_info=True)
            raise
    
    def _get_recurrence_text(self, recurrence_type: str) -> str:
        """Get recurrence type text in Russian"""
        mapping = {
            "daily": "день",
            "weekly": "неделя",
            "monthly": "месяц",
        }
        return mapping.get(recurrence_type, recurrence_type)
    
    def _format_recurrence(self, recurrence_type: str, interval: int) -> str:
        """Format recurrence text"""
        text = self._get_recurrence_text(recurrence_type)
        
        if interval == 1:
            if recurrence_type == "daily":
                return "ежедневно"
            elif recurrence_type == "weekly":
                return "еженедельно"
            elif recurrence_type == "monthly":
                return "ежемесячно"
        
        return f"каждые {interval} {text}"
