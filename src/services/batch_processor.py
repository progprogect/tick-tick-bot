"""
Batch processing service for bulk operations
"""

from typing import List, Dict, Any, Callable, Awaitable, Optional
from datetime import datetime, timedelta
from src.api.ticktick_client import TickTickClient
from src.config.constants import BATCH_SIZE
from src.utils.logger import logger


class BatchProcessor:
    """Service for batch processing operations"""
    
    def __init__(self, ticktick_client: TickTickClient):
        """
        Initialize batch processor
        
        Args:
            ticktick_client: TickTick API client
        """
        self.client = ticktick_client
        self.logger = logger
    
    async def process_batch(
        self,
        items: List[Dict[str, Any]],
        processor: Callable[[Dict[str, Any]], Awaitable[Any]],
        batch_size: int = BATCH_SIZE,
    ) -> int:
        """
        Process items in batches
        
        Args:
            items: List of items to process
            processor: Async function to process each item
            batch_size: Number of items per batch
            
        Returns:
            Number of successfully processed items
        """
        processed = 0
        failed = 0
        
        for i in range(0, len(items), batch_size):
            batch = items[i:i + batch_size]
            self.logger.info(f"Processing batch {i // batch_size + 1} ({len(batch)} items)")
            
            for item in batch:
                try:
                    await processor(item)
                    processed += 1
                except Exception as e:
                    self.logger.error(f"Error processing item {item.get('id', 'unknown')}: {e}")
                    failed += 1
            
            # Small delay between batches to avoid rate limiting
            if i + batch_size < len(items):
                import asyncio
                await asyncio.sleep(0.5)
        
        self.logger.info(f"Batch processing complete: {processed} succeeded, {failed} failed")
        
        return processed
    
    async def move_overdue_tasks(
        self,
        from_date: datetime,
        to_date: datetime,
        target_project_id: Optional[str] = None,
    ) -> int:
        """
        Move overdue tasks from one date to another
        
        Args:
            from_date: Source date (deprecated, kept for backward compatibility)
            to_date: Target date
            target_project_id: Target project ID (optional)
            
        Returns:
            Number of moved tasks
        """
        try:
            from datetime import timezone, timedelta
            from src.config.constants import USER_TIMEZONE_OFFSET
            
            # Get current time with user timezone for filtering overdue tasks
            user_tz = timezone(timedelta(hours=USER_TIMEZONE_OFFSET))
            now = datetime.now(user_tz)
            
            # Get all incomplete tasks (without date filter to find all overdue tasks)
            # Note: GET endpoint may not work, so we return 0 if it fails
            try:
                tasks = await self.client.get_tasks(
                    status=0,  # Incomplete only
                    # Don't filter by date - we need to find all overdue tasks regardless of their date
                )
            except Exception as get_error:
                # GET endpoint doesn't work, return 0 with informative message
                self.logger.warning(f"Cannot get tasks from TickTick API: {get_error}")
                return 0
            
            # Filter overdue tasks: tasks with dueDate < current date
            overdue_tasks = []
            for task in tasks:
                if task.get("status") == 0 and task.get("dueDate"):
                    try:
                        # Parse task due date
                        task_due_date_str = task["dueDate"]
                        # Handle different date formats
                        if 'Z' in task_due_date_str:
                            task_due_date_str = task_due_date_str.replace('Z', '+00:00')
                        elif '+' not in task_due_date_str and '-' not in task_due_date_str[-6:]:
                            # If no timezone info, assume UTC
                            task_due_date_str = task_due_date_str + '+00:00'
                        
                        task_due_date = datetime.fromisoformat(task_due_date_str)
                        
                        # Ensure timezone-aware
                        if task_due_date.tzinfo is None:
                            task_due_date = task_due_date.replace(tzinfo=timezone.utc)
                        
                        # Convert to user timezone for comparison
                        task_due_date = task_due_date.astimezone(user_tz)
                        
                        # Check if task is overdue: dueDate < current date/time
                        # Compare only dates (not time) for overdue detection
                        if task_due_date.date() < now.date():
                            overdue_tasks.append(task)
                            self.logger.debug(
                                f"Found overdue task: {task.get('title', 'N/A')} "
                                f"(due: {task_due_date.date()}, now: {now.date()})"
                            )
                    except Exception as parse_error:
                        self.logger.warning(
                            f"Failed to parse dueDate for task {task.get('id', 'unknown')}: {parse_error}"
                        )
                        continue
            
            if not overdue_tasks:
                self.logger.info("No overdue tasks found")
                return 0
            
            self.logger.info(f"Found {len(overdue_tasks)} overdue tasks")
            
            # Process in batches
            # Import for date formatting
            from src.api.ticktick_client import _format_date_for_ticktick
            from src.services.task_cache import TaskCacheService
            
            cache = TaskCacheService()
            
            async def update_task_date(task: Dict[str, Any]):
                """
                Update due date for a single overdue task
                """
                try:
                    task_id = task.get("id")
                    task_title = task.get("title", "")
                    task_project_id = task.get("projectId")
                    
                    # Ensure task is in cache
                    if not cache.get_task_data(task_id):
                        cache.save_task(
                            task_id=task_id,
                            title=task_title,
                            project_id=task_project_id,
                            status=task.get("status", 0),
                        )
                    
                    # Format target date to ISO string with UTC+3 timezone
                    # to_date is datetime, convert to UTC+3 ISO format
                    from datetime import timezone, timedelta
                    from src.config.constants import USER_TIMEZONE_OFFSET
                    
                    user_tz = timezone(timedelta(hours=USER_TIMEZONE_OFFSET))
                    
                    # Ensure to_date is timezone-aware
                    if to_date.tzinfo is None:
                        to_date_tz = to_date.replace(tzinfo=user_tz)
                    else:
                        to_date_tz = to_date.astimezone(user_tz)
                    
                    # Format as ISO string with UTC+3
                    due_date_iso = to_date_tz.strftime('%Y-%m-%dT%H:%M:%S+03:00')
                    
                    # Format for TickTick API (converts UTC+3 to UTC format)
                    due_date_formatted = _format_date_for_ticktick(due_date_iso)
                    
                    # Update task: only change dueDate, optionally move to target project
                    update_params = {
                        "due_date": due_date_formatted,
                    }
                    
                    # If target project is specified, move task to that project
                    if target_project_id:
                        update_params["project_id"] = target_project_id
                    
                    # Update task via API
                    await self.client.update_task(
                        task_id=task_id,
                        **update_params
                    )
                    
                    self.logger.debug(f"Updated task {task_id} due date to {due_date_iso}")
                    
                except Exception as update_error:
                    # Log error but continue with other tasks
                    error_msg = str(update_error)
                    if "500" in error_msg or "404" in error_msg or "not found" in error_msg.lower():
                        self.logger.warning(f"Cannot update task {task.get('id')}: {error_msg}")
                    else:
                        self.logger.error(f"Error updating task {task.get('id')}: {update_error}")
                    # Don't raise - continue with other tasks
            
            processed = await self.process_batch(overdue_tasks, update_task_date)
            
            return processed
            
        except Exception as e:
            self.logger.error(f"Error moving overdue tasks: {e}", exc_info=True)
            # Return 0 instead of raising to avoid breaking the flow
            return 0

