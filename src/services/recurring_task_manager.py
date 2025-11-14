"""
Recurring task management service
"""

from typing import Optional, Tuple
from datetime import timezone
from src.api.ticktick_client import TickTickClient
from src.models.command import ParsedCommand, Recurrence
from src.utils.logger import logger
from src.utils.date_utils import get_current_datetime


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
    
    @staticmethod
    def _build_repeat_flag(recurrence: Recurrence) -> str:
        """
        Build RRULE format string from recurrence
        
        Args:
            recurrence: Recurrence object with type and interval
            
        Returns:
            RRULE format string (e.g., "RRULE:FREQ=DAILY;INTERVAL=1")
        """
        recurrence_type = recurrence.type.upper()  # DAILY, WEEKLY, MONTHLY
        interval = recurrence.interval or 1
        
        # Build RRULE according to RFC 5545
        # Format: "RRULE:FREQ=DAILY;INTERVAL=1"
        return f"RRULE:FREQ={recurrence_type};INTERVAL={interval}"
    
    @staticmethod
    def _determine_start_date(due_date: Optional[str] = None) -> str:
        """
        Determine startDate for recurring task
        
        IMPORTANT: TickTick API requires startDate for recurring tasks.
        If due_date is provided, use it as startDate.
        If not, use current date as startDate.
        
        Args:
            due_date: Optional due date in ISO format
            
        Returns:
            Start date in TickTick API format (yyyy-MM-dd'T'HH:mm:ss+0000)
        """
        from datetime import datetime
        
        if due_date:
            # Parse due_date and use it as startDate
            try:
                due_dt = datetime.fromisoformat(due_date.replace('Z', '+00:00'))
                # Convert to UTC for TickTick API format
                if due_dt.tzinfo:
                    due_dt_utc = due_dt.astimezone(timezone.utc)
                else:
                    due_dt_utc = due_dt.replace(tzinfo=timezone.utc)
                return due_dt_utc.strftime('%Y-%m-%dT%H:%M:%S+0000')
            except:
                # If parsing fails, use current date in UTC
                current_utc = get_current_datetime().astimezone(timezone.utc)
                return current_utc.strftime('%Y-%m-%dT%H:%M:%S+0000')
        else:
            # Use current date as startDate (convert to UTC for API)
            current_utc = get_current_datetime().astimezone(timezone.utc)
            return current_utc.strftime('%Y-%m-%dT%H:%M:%S+0000')
    
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
            
            # Build repeat flag using shared method
            repeat_flag = self._build_repeat_flag(command.recurrence)
            
            # Determine start date using shared method
            start_date = self._determine_start_date(command.due_date)
            
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
            
            interval = command.recurrence.interval or 1
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
