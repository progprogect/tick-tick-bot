"""
Universal task modifier with contextual operations
"""

from typing import Dict, Any, Optional, List
from src.api.ticktick_client import TickTickClient
from src.services.task_cache import TaskCacheService
from src.models.command import FieldModification, FieldModifier
from src.utils.logger import logger
from src.utils.formatters import format_task_updated


class TaskModifier:
    """Universal task modifier with contextual operations"""
    
    def __init__(self, ticktick_client: TickTickClient):
        """
        Initialize task modifier
        
        Args:
            ticktick_client: TickTick API client
        """
        self.client = ticktick_client
        self.cache = TaskCacheService()
        self.logger = logger
    
    async def modify_task(
        self,
        task_id: str,
        modifications: Dict[str, FieldModification],
        task_identifier: Optional[str] = None,
    ) -> str:
        """
        Modify task with multiple field modifications in one API call
        
        Args:
            task_id: Task ID
            modifications: Dictionary of field modifications
            task_identifier: Optional task identifier for logging
            
        Returns:
            Success message
        """
        try:
            # 1. Get current task data from cache
            current_data = self.cache.get_task_data(task_id)
            if not current_data:
                self.logger.warning(f"Task {task_id} not found in cache, some modifications may not work correctly")
                current_data = {}
            
            # 2. Apply each modification
            update_data = {}
            for field_name, modification in modifications.items():
                processed_value = self._apply_modification(
                    field_name,
                    modification,
                    current_data,
                )
                if processed_value is not None:
                    update_data[field_name] = processed_value
            
            if not update_data:
                raise ValueError("Нет изменений для применения")
            
            # 3. Map field names to TickTick API format
            api_data = await self._map_to_api_format(task_id, update_data, current_data)
            
            # 4. One API request
            await self.client.update_task(task_id, **api_data)
            
            # 5. Update cache
            self._update_cache(task_id, update_data, current_data)
            
            # 6. Format response
            task_title = current_data.get('title', task_identifier or 'Задача')
            # Prepare task dict for formatter (needs title and update_data merged)
            task_dict = {"title": task_title}
            task_dict.update(update_data)
            return format_task_updated(task_dict)
            
        except Exception as e:
            self.logger.error(f"Error modifying task: {e}", exc_info=True)
            raise
    
    def _apply_modification(
        self,
        field_name: str,
        modification: FieldModification,
        current_data: Dict[str, Any],
    ) -> Any:
        """
        Apply modification to field
        
        Args:
            field_name: Field name
            modification: Field modification
            current_data: Current task data
            
        Returns:
            Processed value or None
        """
        if modification.modifier == FieldModifier.REPLACE:
            return modification.value
        
        elif modification.modifier == FieldModifier.MERGE:
            if field_name == "tags":
                current_tags = current_data.get('tags', [])
                if not isinstance(current_tags, list):
                    current_tags = []
                new_tags = modification.value if isinstance(modification.value, list) else [modification.value]
                # Merge and remove duplicates
                merged = list(set(current_tags + new_tags))
                return merged
            elif field_name == "reminders":
                current_reminders = current_data.get('reminders', [])
                if not isinstance(current_reminders, list):
                    current_reminders = []
                new_reminders = modification.value if isinstance(modification.value, list) else [modification.value]
                # Merge and remove duplicates
                merged = list(set(current_reminders + new_reminders))
                return merged
            else:
                # For other fields, merge means append to list or combine
                current_value = current_data.get(field_name, [])
                if not isinstance(current_value, list):
                    current_value = [current_value] if current_value else []
                new_value = modification.value if isinstance(modification.value, list) else [modification.value]
                return current_value + new_value
        
        elif modification.modifier == FieldModifier.APPEND:
            if field_name in ["notes", "content"]:
                current_value = current_data.get('notes', '') or current_data.get('content', '')
                new_value = modification.value
                if current_value:
                    return f"{current_value}\n\n{new_value}"
                return new_value
            else:
                # For other fields, append means add to end
                current_value = current_data.get(field_name, '')
                return f"{current_value}{modification.value}" if current_value else modification.value
        
        elif modification.modifier == FieldModifier.REMOVE:
            if field_name == "tags":
                current_tags = current_data.get('tags', [])
                if not isinstance(current_tags, list):
                    current_tags = []
                tags_to_remove = modification.value if isinstance(modification.value, list) else [modification.value]
                return [tag for tag in current_tags if tag not in tags_to_remove]
            elif field_name == "reminders":
                current_reminders = current_data.get('reminders', [])
                if not isinstance(current_reminders, list):
                    current_reminders = []
                reminders_to_remove = modification.value if isinstance(modification.value, list) else [modification.value]
                return [rem for rem in current_reminders if rem not in reminders_to_remove]
            elif field_name in ["dueDate", "due_date", "startDate", "start_date"]:
                # For date fields, use special marker to indicate removal
                # This will be handled in _map_to_api_format to send null to API
                return "__REMOVE_DATE__"
            else:
                # For other fields, remove means set to None or empty
                return None
        
        return modification.value
    
    async def _map_to_api_format(
        self,
        task_id: str,
        update_data: Dict[str, Any],
        current_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Map internal field names to TickTick API format
        
        Args:
            task_id: Task ID
            update_data: Update data with internal field names
            current_data: Current task data
            
        Returns:
            API-formatted data
        """
        api_data = {
            "id": task_id,
        }
        
        # Get projectId from cache if not in update_data
        project_id = update_data.get("projectId") or current_data.get('project_id')
        if project_id:
            api_data["projectId"] = project_id
        else:
            # Try to get from cache
            cached = self.cache.get_task_data(task_id)
            if cached and cached.get('project_id'):
                api_data["projectId"] = cached.get('project_id')
            else:
                # Try to get from API if not in cache
                try:
                    all_tasks = await self.client.get_tasks()
                    for task in all_tasks:
                        if task.get('id') == task_id:
                            project_id = task.get('projectId')
                            if project_id:
                                api_data["projectId"] = project_id
                                # Save to cache for future use
                                self.cache.save_task(
                                    task_id=task_id,
                                    title=task.get('title', ''),
                                    project_id=project_id,
                                )
                                self.logger.debug(f"Got projectId from API for task {task_id}: {project_id}")
                                break
                    
                    if not api_data.get("projectId"):
                        raise ValueError(f"projectId is required for update, but not found in cache or API for task {task_id}")
                except Exception as api_error:
                    self.logger.warning(f"Failed to get projectId from API: {api_error}")
                    raise ValueError(f"projectId is required for update, but not found in cache or API for task {task_id}")
        
        # Import date formatting function
        from src.api.ticktick_client import _format_date_for_ticktick
        
        # Map field names and format dates
        field_mapping = {
            "dueDate": "dueDate",
            "due_date": "dueDate",
            "startDate": "startDate",
            "start_date": "startDate",
            "priority": "priority",
            "tags": "tags",
            "notes": "content",
            "content": "content",
            "title": "title",
            "projectId": "projectId",
            "project_id": "projectId",
            "reminders": "reminders",
            "repeatFlag": "repeatFlag",
            "repeat_flag": "repeatFlag",
        }
        
        # Fields that need date formatting
        date_fields = {"dueDate", "startDate", "completedTime"}
        
        for field_name, value in update_data.items():
            api_field = field_mapping.get(field_name, field_name)
            
            # Handle date field removal (special marker)
            if api_field in date_fields and value == "__REMOVE_DATE__":
                # Set to null to remove date field in TickTick API
                api_data[api_field] = None
            # Format date fields according to TickTick API format
            elif api_field in date_fields and value is not None:
                api_data[api_field] = _format_date_for_ticktick(str(value))
            else:
                api_data[api_field] = value
        
        return api_data
    
    def _update_cache(
        self,
        task_id: str,
        update_data: Dict[str, Any],
        current_data: Dict[str, Any],
    ):
        """
        Update cache with new data
        
        Args:
            task_id: Task ID
            update_data: Update data
            current_data: Current task data
        """
        # Update cache fields
        for field_name, value in update_data.items():
            cache_field = field_name
            if field_name == "content":
                cache_field = "notes"
            elif field_name == "projectId":
                cache_field = "project_id"
            elif field_name == "dueDate":
                cache_field = "due_date"
            
            self.cache.update_task_field(task_id, cache_field, value)
        
        # Update updated_at timestamp
        from datetime import datetime
        self.cache.update_task_field(task_id, "updated_at", datetime.now().isoformat())

