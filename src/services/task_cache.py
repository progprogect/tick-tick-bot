"""
Task cache service for storing task ID to title mapping
"""

import json
import os
from typing import Optional, Dict, List, Any
from pathlib import Path
from datetime import datetime
from src.utils.logger import logger
from src.utils.date_utils import get_current_datetime


class TaskCacheService:
    """Service for caching task IDs using JSON file"""
    
    def __init__(self, cache_file: Optional[str] = None):
        """
        Initialize task cache service
        
        Args:
            cache_file: Path to cache file (optional, uses env var or default)
        """
        # Use environment variable or default to temporary storage
        if cache_file is None:
            cache_file = os.getenv("CACHE_FILE_PATH", "/tmp/task_cache.json")
        self.cache_file = Path(cache_file)
        self.logger = logger
        self._cache: Dict[str, Dict] = {}
        self._load_cache()
    
    def _load_cache(self):
        """Load cache from file"""
        try:
            if self.cache_file.exists():
                with open(self.cache_file, 'r', encoding='utf-8') as f:
                    self._cache = json.load(f)
                self.logger.debug(f"Loaded {len(self._cache)} tasks from cache")
            else:
                self._cache = {}
        except Exception as e:
            self.logger.warning(f"Failed to load cache: {e}")
            self._cache = {}
    
    def _save_cache(self):
        """Save cache to file"""
        try:
            # Ensure directory exists
            self.cache_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump(self._cache, f, ensure_ascii=False, indent=2)
        except Exception as e:
            self.logger.warning(f"Failed to save cache: {e}. Using in-memory cache only.")
    
    def get_task_id_by_title(self, title: str, project_id: Optional[str] = None) -> Optional[str]:
        """
        Get task ID by title (flexible matching)
        
        Args:
            title: Task title
            project_id: Project ID (optional)
            
        Returns:
            Task ID or None
        """
        # Reload cache before search to get latest data (in case another process updated it)
        self._load_cache()
        
        # Normalize title: lowercase, strip, normalize spaces
        def normalize_title(t: str) -> str:
            """Normalize title for comparison"""
            if not t:
                return ""
            # Lowercase, strip, replace multiple spaces with single space
            import re
            normalized = re.sub(r'\s+', ' ', t.lower().strip())
            return normalized
        
        search_title_normalized = normalize_title(title)
        self.logger.debug(f"[TaskCache] Searching for title: '{title}' (normalized: '{search_title_normalized}')")
        
        # First, try exact match (after normalization)
        for task_id, task_data in self._cache.items():
            # Skip completed or deleted tasks
            if task_data.get('status') in ('completed', 'deleted'):
                continue
            
            cached_title = task_data.get('title', '')
            cached_title_normalized = normalize_title(cached_title)
            
            if cached_title_normalized == search_title_normalized:
                # If project_id specified, check it matches
                if project_id is None or task_data.get('project_id') == project_id:
                    self.logger.debug(f"[TaskCache] Exact match found: '{cached_title}' -> {task_id}")
                    return task_id
        
        # If exact match not found, try partial match (contains)
        self.logger.debug(f"[TaskCache] Exact match not found, trying partial match...")
        matches = []
        for task_id, task_data in self._cache.items():
            # Skip completed or deleted tasks
            if task_data.get('status') in ('completed', 'deleted'):
                continue
            
            cached_title = task_data.get('title', '')
            cached_title_normalized = normalize_title(cached_title)
            
            # Check if search title is contained in cached title or vice versa
            if (search_title_normalized in cached_title_normalized or 
                cached_title_normalized in search_title_normalized):
                # If project_id specified, check it matches
                if project_id is None or task_data.get('project_id') == project_id:
                    matches.append((task_id, cached_title, cached_title_normalized))
        
        if matches:
            # Prefer longer match (more specific)
            matches.sort(key=lambda x: len(x[2]), reverse=True)
            best_match = matches[0]
            self.logger.info(f"[TaskCache] Partial match found: '{best_match[1]}' (normalized: '{best_match[2]}') -> {best_match[0]} for search '{title}'")
            if len(matches) > 1:
                self.logger.warning(f"[TaskCache] Multiple matches found: {[m[1] for m in matches]}, using '{best_match[1]}'")
            return best_match[0]
        
        # Log available tasks for debugging
        active_tasks = [
            (tid, tdata.get('title', '')) 
            for tid, tdata in self._cache.items() 
            if tdata.get('status') not in ('completed', 'deleted')
        ]
        if active_tasks:
            task_titles = [f"'{t[1]}' (id: {t[0]})" for t in active_tasks[:10]]
            self.logger.debug(f"[TaskCache] Available tasks in cache: {', '.join(task_titles)}{'...' if len(active_tasks) > 10 else ''}")
        
        self.logger.warning(f"[TaskCache] Task not found: '{title}' (normalized: '{search_title_normalized}')")
        return None
    
    def save_task(
        self, 
        task_id: str, 
        title: str, 
        project_id: Optional[str] = None,
        column_id: Optional[str] = None,
        original_task_id: Optional[str] = None,
        status: str = "active",
        tags: Optional[List[str]] = None,
        notes: Optional[str] = None,
        reminders: Optional[List[str]] = None,
        repeat_flag: Optional[str] = None,
        sort_order: Optional[int] = None,
        kind: Optional[str] = None,
    ):
        """
        Save task to cache
        
        Args:
            task_id: Task ID
            title: Task title
            project_id: Project ID (optional)
            column_id: Column ID (optional, for Kanban projects)
            original_task_id: Original task ID if this is a replacement (optional)
            status: Task status (active, completed, deleted)
            tags: Tags list (optional)
            notes: Notes content (optional)
            reminders: Reminders list (optional)
            repeat_flag: Repeat flag in RRULE format (optional)
            kind: Task kind ("TEXT", "NOTE", "CHECKLIST") (optional)
        """
        from datetime import datetime
        self._load_cache()
        
        # Get existing data if exists to preserve tags, notes, reminders, repeat_flag
        existing_data = self._cache.get(task_id, {})
        
        self._cache[task_id] = {
            'title': title,
            'project_id': project_id if project_id is not None else existing_data.get('project_id'),
            'column_id': column_id if column_id is not None else existing_data.get('column_id'),
            'status': status,
            'original_task_id': original_task_id or existing_data.get('original_task_id'),
            'tags': tags if tags is not None else existing_data.get('tags', []),
            'notes': notes if notes is not None else existing_data.get('notes', ''),
            'reminders': reminders if reminders is not None else existing_data.get('reminders', []),
            'repeat_flag': repeat_flag if repeat_flag is not None else existing_data.get('repeat_flag'),
            'sort_order': sort_order if sort_order is not None else existing_data.get('sort_order'),
            'kind': kind if kind is not None else existing_data.get('kind', 'TEXT'),
            'created_at': existing_data.get('created_at', get_current_datetime().isoformat()),
            'updated_at': get_current_datetime().isoformat(),
        }
        self._save_cache()
        self.logger.debug(f"Cached task: {title} -> {task_id} (status: {status})")
    
    def update_task_field(self, task_id: str, field: str, value: Any):
        """
        Update a specific field in task cache
        
        Args:
            task_id: Task ID
            field: Field name to update
            value: New value
        """
        self._load_cache()
        if task_id in self._cache:
            self._cache[task_id][field] = value
            self._cache[task_id]['updated_at'] = get_current_datetime().isoformat()
            self._save_cache()
            self.logger.debug(f"Updated field {field} for task {task_id}")
        else:
            self.logger.warning(f"Task {task_id} not found in cache, cannot update field {field}")
    
    def get_task_data(self, task_id: str) -> Optional[Dict]:
        """
        Get task data from cache
        
        Args:
            task_id: Task ID
            
        Returns:
            Task data or None
        """
        self._load_cache()
        task_data = self._cache.get(task_id)
        if task_data:
            # Convert old cache format to new format if needed
            if 'status' not in task_data:
                task_data['status'] = 'active'
            if 'created_at' not in task_data:
                task_data['created_at'] = get_current_datetime().isoformat()
            if 'updated_at' not in task_data:
                task_data['updated_at'] = get_current_datetime().isoformat()
        return task_data
    
    def mark_as_completed(self, task_id: str):
        """Mark task as completed in cache"""
        if task_id in self._cache:
            self._cache[task_id]['status'] = 'completed'
            self._cache[task_id]['updated_at'] = get_current_datetime().isoformat()
            self._save_cache()
    
    def mark_as_deleted(self, task_id: str):
        """Mark task as deleted in cache"""
        if task_id in self._cache:
            self._cache[task_id]['status'] = 'deleted'
            self._cache[task_id]['updated_at'] = get_current_datetime().isoformat()
            self._save_cache()
    
    def delete_task(self, task_id: str):
        """
        Delete task from cache
        
        Args:
            task_id: Task ID
        """
        if task_id in self._cache:
            del self._cache[task_id]
            self._save_cache()
            self.logger.debug(f"Deleted task from cache: {task_id}")
    
    def get_completed_tasks(self, project_id: Optional[str] = None) -> List[tuple]:
        """
        Get list of completed task IDs and their project IDs from cache
        
        Args:
            project_id: Optional project ID to filter by
            
        Returns:
            List of tuples (task_id, project_id) for completed tasks
        """
        self._load_cache()
        completed_tasks = []
        for task_id, task_data in self._cache.items():
            if task_data.get('status') == 'completed':
                task_project_id = task_data.get('project_id')
                if project_id is None or task_project_id == project_id:
                    completed_tasks.append((task_id, task_project_id))
        return completed_tasks
    
    async def sync_task_from_api(
        self,
        task_id: str,
        project_id: str,
        client: Any,  # TickTickClient
    ) -> None:
        """
        Synchronize task from API to cache
        
        Gets current task data from API and saves to cache
        
        Args:
            task_id: Task ID
            project_id: Project ID
            client: TickTickClient instance
        """
        try:
            from src.config.constants import TICKTICK_API_VERSION
            
            # Ensure client is authenticated
            if not hasattr(client, 'access_token') or not client.access_token:
                await client.authenticate()
            
            # Get task from API
            task = await client.get(
                endpoint=f"/open/{TICKTICK_API_VERSION}/project/{project_id}/task/{task_id}",
                headers=client._get_headers(),
            )
            
            if isinstance(task, dict):
                # Convert API status to cache status
                api_status = task.get("status", 0)
                cache_status = "completed" if api_status == 2 else "active"
                
                # Save to cache
                self.save_task(
                    task_id=task.get("id", task_id),
                    title=task.get("title", ""),
                    project_id=task.get("projectId", project_id),
                    status=cache_status,
                    tags=task.get("tags", []),
                    notes=task.get("content", ""),
                    reminders=task.get("reminders", []),
                    repeat_flag=task.get("repeatFlag"),
                    sort_order=task.get("sortOrder"),
                )
                self.logger.info(f"[TaskCache] Synced task {task_id} from API to cache")
            else:
                self.logger.warning(f"[TaskCache] Failed to sync task {task_id}: invalid response from API")
        except Exception as e:
            self.logger.warning(f"[TaskCache] Failed to sync task {task_id} from API: {e}", exc_info=True)
    
    async def bulk_sync_tasks_from_project(
        self,
        project_id: str,
        client: Any,  # TickTickClient
    ) -> int:
        """
        Synchronize all tasks from project to cache
        
        Gets all tasks from project using GET /open/v1/project/{projectId}/data
        and saves them to cache
        
        Args:
            project_id: Project ID
            client: TickTickClient instance
            
        Returns:
            Number of tasks synchronized
        """
        try:
            from src.config.constants import TICKTICK_API_VERSION
            
            # Ensure client is authenticated
            if not hasattr(client, 'access_token') or not client.access_token:
                await client.authenticate()
            
            # Get project data (includes tasks)
            response = await client.get(
                endpoint=f"/open/{TICKTICK_API_VERSION}/project/{project_id}/data",
                headers=client._get_headers(),
            )
            
            if isinstance(response, dict) and "tasks" in response:
                tasks = response["tasks"]
                if isinstance(tasks, list):
                    count = 0
                    for task in tasks:
                        # GET /project/{projectId}/data returns only incomplete tasks (status=0)
                        self.save_task(
                            task_id=task.get("id"),
                            title=task.get("title", ""),
                            project_id=task.get("projectId", project_id),
                            status="active",  # Only incomplete tasks are returned
                            tags=task.get("tags", []),
                            notes=task.get("content", ""),
                            reminders=task.get("reminders", []),
                            repeat_flag=task.get("repeatFlag"),
                            sort_order=task.get("sortOrder"),
                        )
                        count += 1
                    
                    self.logger.info(f"[TaskCache] Synced {count} tasks from project {project_id} to cache")
                    return count
                else:
                    self.logger.warning(f"[TaskCache] Invalid tasks format in response for project {project_id}")
                    return 0
            else:
                self.logger.warning(f"[TaskCache] No tasks in response for project {project_id}")
                return 0
        except Exception as e:
            self.logger.warning(f"[TaskCache] Failed to sync tasks from project {project_id}: {e}", exc_info=True)
            return 0

