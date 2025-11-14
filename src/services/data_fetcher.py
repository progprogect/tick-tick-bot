"""
Data fetcher service for retrieving data from cache and API
"""

import re
from typing import Optional, Dict, List, Any
from datetime import datetime, timedelta
from src.api.ticktick_client import TickTickClient
from src.services.task_cache import TaskCacheService
from src.services.project_cache_service import ProjectCacheService
from src.services.column_cache_service import ColumnCacheService
from src.utils.logger import logger
from src.utils.date_utils import get_current_datetime


def _clean_project_name(name: str) -> str:
    """Remove emojis and extra spaces from project name for matching"""
    if not name:
        return ""
    # Remove emojis (Unicode ranges for emojis)
    emoji_pattern = re.compile(
        "["
        "\U0001F600-\U0001F64F"  # emoticons
        "\U0001F300-\U0001F5FF"  # symbols & pictographs
        "\U0001F680-\U0001F6FF"  # transport & map symbols
        "\U0001F1E0-\U0001F1FF"  # flags (iOS)
        "\U00002702-\U000027B0"
        "\U000024C2-\U0001F251"
        "]+", flags=re.UNICODE
    )
    cleaned = emoji_pattern.sub('', name).strip()
    return cleaned


class DataFetcher:
    """Service for fetching data from cache and API based on GPT requirements"""
    
    def __init__(self, ticktick_client: TickTickClient):
        """
        Initialize data fetcher
        
        Args:
            ticktick_client: TickTick API client
        """
        self.client = ticktick_client
        self.cache = TaskCacheService()
        self.project_cache = ProjectCacheService(ticktick_client)
        self.column_cache = ColumnCacheService(ticktick_client)
        self.logger = logger
        
        # Cache for all tasks (TTL: 2 minutes)
        self._all_tasks_cache: Optional[List[Dict[str, Any]]] = None
        self._all_tasks_cache_time: Optional[datetime] = None
        self._all_tasks_cache_ttl = timedelta(minutes=2)
    
    async def _get_all_tasks(self) -> List[Dict[str, Any]]:
        """
        Get all tasks from all projects (with caching)
        
        Returns:
            List of all tasks
        """
        # Check cache
        if (self._all_tasks_cache is not None and 
            self._all_tasks_cache_time is not None and
            get_current_datetime() - self._all_tasks_cache_time < self._all_tasks_cache_ttl):
            self.logger.info(f"[DataFetcher] Using cached all tasks ({len(self._all_tasks_cache)} tasks)")
            return self._all_tasks_cache
        
        # Fetch all tasks (including completed ones)
        self.logger.info(f"[DataFetcher] ===== FETCHING ALL TASKS FROM ALL PROJECTS =====")
        
        # Get incomplete tasks from API (GET /project/{projectId}/data returns only status=0)
        # ⚠️ ВАЖНО: API возвращает максимум 99 задач из каждого проекта (ограничение TickTick API)
        incomplete_tasks = await self.client.get_tasks()
        self.logger.info(f"[DataFetcher] Retrieved {len(incomplete_tasks)} incomplete tasks from API")
        
        # Create a set of task IDs from API to check for duplicates
        api_task_ids = {task.get("id") for task in incomplete_tasks if task.get("id")}
        
        # Start with incomplete tasks from API
        all_tasks = list(incomplete_tasks)
        
        # Load cache and add tasks from cache that are NOT in API response
        # This includes:
        # 1. Completed tasks (status=2) - API не возвращает их
        # 2. Active tasks beyond the 99 limit - API возвращает только первые 99
        self.cache._load_cache()  # Ensure cache is loaded
        tasks_from_cache = []
        cache_task_ids = set()
        
        # Log cache size for debugging
        self.logger.info(f"[DataFetcher] Cache contains {len(self.cache._cache)} tasks")
        
        for task_id, task_data in self.cache._cache.items():
            if not task_id:
                continue
            
            # Skip deleted tasks
            if task_data.get("status") == "deleted":
                continue
            
            # Skip if already in API response
            if task_id in api_task_ids:
                continue
            
            # Convert cache format to API format
            cache_task = {
                "id": task_id,
                "title": task_data.get("title", ""),
                "projectId": task_data.get("project_id"),
                "status": 2 if task_data.get("status") == "completed" else 0,
            }
            
            # Add additional fields if available in cache
            if "dueDate" in task_data:
                cache_task["dueDate"] = task_data["dueDate"]
            if "startDate" in task_data:
                cache_task["startDate"] = task_data["startDate"]
            if "priority" in task_data:
                cache_task["priority"] = task_data["priority"]
            if "sort_order" in task_data:
                cache_task["sortOrder"] = task_data["sort_order"]
            
            tasks_from_cache.append(cache_task)
            cache_task_ids.add(task_id)
        
        if tasks_from_cache:
            self.logger.info(
                f"[DataFetcher] Adding {len(tasks_from_cache)} tasks from cache "
                f"(not in API response: completed or beyond 99 limit)"
            )
            all_tasks.extend(tasks_from_cache)
        
        # Sort all tasks by timestamp from ID (more reliable than sortOrder)
        # ObjectId contains timestamp in first 8 hex characters
        def get_task_timestamp(task):
            task_id = task.get("id", "")
            if task_id and len(task_id) >= 8:
                try:
                    # Extract timestamp from first 8 hex chars
                    hex_timestamp = task_id[:8]
                    timestamp = int(hex_timestamp, 16)
                    return timestamp
                except:
                    pass
            # Fallback to sortOrder if ID parsing fails
            return task.get("sortOrder", 0)
        
        all_tasks = sorted(
            all_tasks,
            key=get_task_timestamp,
            reverse=True  # Higher timestamp = newer task
        )
        self.logger.info(
            f"[DataFetcher] Sorted all {len(all_tasks)} tasks by sortOrder "
            f"(across all projects, most recent first)"
        )
        
        # Log all task titles for debugging
        if all_tasks:
            task_titles = [t.get("title", "") for t in all_tasks]
            self.logger.info(f"[DataFetcher] All task titles ({len(task_titles)} tasks): {task_titles}")
        
        # Update cache
        self._all_tasks_cache = all_tasks
        self._all_tasks_cache_time = get_current_datetime()
        self.logger.info(
            f"[DataFetcher] Cached {len(all_tasks)} tasks "
            f"({len(incomplete_tasks)} incomplete from API + {len(tasks_from_cache)} from cache, TTL: 2 minutes)"
        )
        
        return all_tasks
    
    async def fetch_data_requirements(self, requirements: Dict[str, Any]) -> Dict[str, Any]:
        """
        Fetch data based on requirements from GPT
        
        Args:
            requirements: Dictionary with required_data structure from GPT
            
        Returns:
            Dictionary with fetched data
        """
        self.logger.info(f"[DataFetcher] Starting data fetch for requirements: {requirements}")
        
        if not self.client:
            self.logger.error("[DataFetcher] Client is None!")
            raise ValueError("TickTick client not available")
        
        self.logger.debug(f"[DataFetcher] Client type: {type(self.client).__name__}")
        self.logger.debug(f"[DataFetcher] Client has access_token: {hasattr(self.client, 'access_token') and bool(self.client.access_token)}")
        
        fetched_data = {
            "tasks": {},
            "projects": {},
            "columns": {},
            "task_data": {},
            "current_task_data": {},
            "all_tasks": [],  # Always include all tasks
        }
        
        # ALWAYS fetch all tasks first (for GPT context)
        self.logger.info(f"[DataFetcher] ===== FETCHING ALL TASKS FOR GPT CONTEXT =====")
        all_tasks = await self._get_all_tasks()
        fetched_data["all_tasks"] = all_tasks
        self.logger.info(f"[DataFetcher] Fetched {len(all_tasks)} tasks for GPT context")
        
        # Log task titles for debugging
        if all_tasks:
            task_titles = [t.get("title", "") for t in all_tasks[:20]]
            self.logger.info(f"[DataFetcher] Sample task titles (first 20): {task_titles}")
            if len(all_tasks) > 20:
                self.logger.info(f"[DataFetcher] ... and {len(all_tasks) - 20} more tasks")
        
        required_data = requirements.get("required_data", {})
        self.logger.debug(f"[DataFetcher] Required data: {required_data}")
        
        # Fetch tasks by title
        task_titles = required_data.get("task_by_title", [])
        self.logger.info(f"[DataFetcher] ===== FETCHING TASKS BY TITLE =====")
        self.logger.info(f"[DataFetcher] Task titles to fetch: {task_titles}")
        self.logger.info(f"[DataFetcher] Number of tasks to fetch: {len(task_titles)}")
        for title in task_titles:
            project_id = required_data.get("project_by_name_for_task", {}).get(title)
            self.logger.debug(f"[DataFetcher] Fetching task '{title}' (project_id: {project_id})")
            task = await self.fetch_task_by_title(title, project_id)
            if task:
                fetched_data["tasks"][title] = task
                self.logger.info(f"[DataFetcher] Task '{title}' found: {task.get('id')}")
            else:
                fetched_data["tasks"][title] = None
                self.logger.warning(f"[DataFetcher] Task '{title}' not found")
        
        # Fetch projects by name
        # НЕ запрашиваем проекты для create_project и delete_project
        # Для create_project название проекта - это название НОВОГО проекта, не существующего
        # Для delete_project проверка наличия проекта выполняется в ProjectManager.delete_project()
        action_type = requirements.get("action_type", "")
        project_names = required_data.get("project_by_name", [])
        
        if action_type in ["create_project", "delete_project"]:
            # Для create_project и delete_project не нужно искать проекты
            self.logger.info(
                f"[DataFetcher] Skipping project fetch for {action_type} - "
                f"project existence check not needed"
            )
        else:
            # Для других действий ищем проекты
            self.logger.info(f"[DataFetcher] Fetching {len(project_names)} projects by name: {project_names}")
            for name in project_names:
                self.logger.debug(f"[DataFetcher] Fetching project '{name}'")
                project = await self.fetch_project_by_name(name)
                if project:
                    fetched_data["projects"][name] = project
                    self.logger.info(f"[DataFetcher] Project '{name}' found: {project.get('id')}")
                else:
                    fetched_data["projects"][name] = None
                    self.logger.warning(f"[DataFetcher] Project '{name}' not found")
        
        # Fetch columns by name (requires project_id)
        column_names = required_data.get("column_by_name", [])
        if column_names:
            self.logger.info(f"[DataFetcher] Fetching {len(column_names)} columns by name: {column_names}")
            # Need to get project_id first - try to get from task or use first project
            project_id_for_columns = None
            # Try to get project_id from task if available
            if task_titles and fetched_data.get("tasks"):
                first_task = next((t for t in fetched_data["tasks"].values() if t), None)
                if first_task:
                    project_id_for_columns = first_task.get("projectId")
            # If no task found, try to get from projects
            if not project_id_for_columns and project_names and fetched_data.get("projects"):
                first_project = next((p for p in fetched_data["projects"].values() if p), None)
                if first_project:
                    project_id_for_columns = first_project.get("id")
            
            if project_id_for_columns:
                columns = await self.column_cache.get_columns(project_id_for_columns)
                for column_name in column_names:
                    column = next((c for c in columns if c.get('name', '').lower() == column_name.lower()), None)
                    if column:
                        fetched_data["columns"][column_name] = column
                        self.logger.info(f"[DataFetcher] Column '{column_name}' found: {column.get('id')}")
                    else:
                        fetched_data["columns"][column_name] = None
                        self.logger.warning(f"[DataFetcher] Column '{column_name}' not found")
            else:
                self.logger.warning(f"[DataFetcher] Cannot fetch columns: project_id not found")
                for column_name in column_names:
                    fetched_data["columns"][column_name] = None
        
        # Fetch task data by task_id
        task_ids = required_data.get("task_data", [])
        for task_id in task_ids:
            task_data = await self.fetch_task_data(task_id)
            if task_data:
                fetched_data["task_data"][task_id] = task_data
            else:
                fetched_data["task_data"][task_id] = None
        
        # Fetch current task data (for merge operations)
        current_task_ids = required_data.get("current_task_data", [])
        for task_id in current_task_ids:
            task_data = await self.fetch_task_data(task_id)
            if task_data:
                fetched_data["current_task_data"][task_id] = task_data
            else:
                fetched_data["current_task_data"][task_id] = None
        
        # Fetch all projects if needed
        if required_data.get("all_projects", False):
            projects = await self.fetch_projects()
            fetched_data["all_projects"] = projects
        
        # Fetch tasks by filters if needed
        if required_data.get("tasks_by_filters"):
            filters = required_data.get("tasks_by_filters", {})
            tasks = await self.fetch_tasks(
                project_id=filters.get("project_id"),
                filters=filters
            )
            fetched_data["tasks_by_filters"] = tasks
        
        self.logger.info(f"[DataFetcher] Data fetch completed: {len(fetched_data.get('tasks', {}))} tasks, "
                         f"{len(fetched_data.get('projects', {}))} projects, "
                         f"{len(fetched_data.get('task_data', {}))} task data entries")
        
        # Log summary of what was found/not found
        tasks_found = sum(1 for t in fetched_data.get('tasks', {}).values() if t is not None)
        tasks_not_found = sum(1 for t in fetched_data.get('tasks', {}).values() if t is None)
        projects_found = sum(1 for p in fetched_data.get('projects', {}).values() if p is not None)
        projects_not_found = sum(1 for p in fetched_data.get('projects', {}).values() if p is None)
        
        self.logger.info(f"[DataFetcher] Summary: {tasks_found} tasks found, {tasks_not_found} not found; "
                        f"{projects_found} projects found, {projects_not_found} not found")
        
        return fetched_data
    
    async def fetch_task_by_title(
        self, 
        title: str, 
        project_id: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Fetch task by title (searches only in API, not in cache)
        
        Args:
            title: Task title
            project_id: Project ID (optional)
            
        Returns:
            Task data or None if not found
        """
        self.logger.info(f"[DataFetcher] Fetching task by title from API: '{title}' (project_id: {project_id})")
        
        # Search only in API
        try:
            self.logger.debug(f"[DataFetcher] Searching in API for task: '{title}'")
            tasks = await self.client.get_tasks(project_id=project_id)
            self.logger.info(f"[DataFetcher] Retrieved {len(tasks)} tasks from API")
            
            # Log ALL task titles for debugging
            if tasks:
                all_titles = [t.get("title", "") for t in tasks]
                self.logger.info(f"[DataFetcher] All task titles from API ({len(all_titles)} tasks): {all_titles}")
                
                # Also log task IDs and projects for debugging
                task_details = [
                    f"'{t.get('title', '')}' (id: {t.get('id', 'N/A')}, projectId: {t.get('projectId', 'N/A')})"
                    for t in tasks[:20]
                ]
                self.logger.debug(f"[DataFetcher] Task details: {task_details}")
            else:
                self.logger.warning(f"[DataFetcher] No tasks returned from API (empty list or None)")
            
            # Normalize for comparison
            def normalize_title(t: str) -> str:
                """Normalize title for comparison"""
                if not t:
                    return ""
                import re
                return re.sub(r'\s+', ' ', t.lower().strip())
            
            search_title_normalized = normalize_title(title)
            self.logger.debug(f"[DataFetcher] Searching for normalized title: '{search_title_normalized}'")
            
            # First try exact match
            matching_task = next(
                (t for t in tasks if normalize_title(t.get("title", "")) == search_title_normalized),
                None
            )
            
            if matching_task:
                self.logger.info(f"[DataFetcher] Exact match found: '{matching_task.get('title')}'")
            else:
                self.logger.debug(f"[DataFetcher] Exact match not found, trying partial match...")
                
                # If exact match not found, try partial match
                matches = []
                for t in tasks:
                    task_title = t.get("title", "")
                    task_title_normalized = normalize_title(task_title)
                    if (search_title_normalized in task_title_normalized or 
                        task_title_normalized in search_title_normalized):
                        matches.append((t, len(task_title_normalized), task_title))
                
                if matches:
                    # Prefer longer match (more specific)
                    matches.sort(key=lambda x: x[1], reverse=True)
                    matching_task = matches[0][0]
                    self.logger.info(f"[DataFetcher] Partial match found in API: '{matches[0][2]}' (normalized: '{normalize_title(matches[0][2])}') for search '{title}' (normalized: '{search_title_normalized}')")
                    if len(matches) > 1:
                        self.logger.warning(f"[DataFetcher] Multiple partial matches found: {[m[2] for m in matches]}, using '{matches[0][2]}'")
            
            if matching_task:
                task_id = matching_task.get("id")
                task_title = matching_task.get("title", title)
                # Cache it for future use (for other operations)
                self.cache.save_task(
                    task_id=task_id,
                    title=task_title,  # Use actual title from API
                    project_id=matching_task.get("projectId") or project_id,
                )
                self.logger.info(f"[DataFetcher] Found task in API: {task_id} ('{task_title}')")
                return matching_task
            else:
                self.logger.warning(f"[DataFetcher] Task not found in API: '{title}' (normalized: '{search_title_normalized}')")
                # Log normalized titles for comparison
                if tasks:
                    normalized_titles = [normalize_title(t.get("title", "")) for t in tasks]
                    self.logger.debug(f"[DataFetcher] Normalized task titles from API: {normalized_titles}")
        except Exception as e:
            self.logger.warning(f"[DataFetcher] Failed to search task in API: {e}", exc_info=True)
        
        self.logger.warning(f"[DataFetcher] Task not found: '{title}' (searched in API only)")
        return None
    
    async def fetch_project_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """
        Fetch project by name
        
        Args:
            name: Project name
            
        Returns:
            Project data or None if not found
        """
        self.logger.debug(f"Fetching project by name: '{name}'")
        
        try:
            projects = await self.client.get_projects()
            
            name_lower = name.lower().strip()
            cleaned_name_lower = _clean_project_name(name).lower()
            
            # First, try exact match (case-insensitive, emoji-insensitive)
            for project in projects:
                project_name = project.get('name', '').strip()
                project_id = project.get('id')
                
                if not project_name or not project_id:
                    continue
                
                cleaned_project_name = _clean_project_name(project_name).lower()
                
                if cleaned_project_name == cleaned_name_lower or cleaned_project_name == name_lower:
                    self.logger.debug(f"Found project: '{project_name}' (ID: {project_id})")
                    return project
            
            # If exact match not found, try partial match
            matches = []
            for project in projects:
                project_name = project.get('name', '').strip()
                project_id = project.get('id')
                
                if not project_name or not project_id:
                    continue
                
                project_name_lower = project_name.lower()
                
                if (name_lower in project_name_lower or project_name_lower in name_lower):
                    matches.append(project)
            
            if matches:
                # Prefer shorter name (more specific)
                matches.sort(key=lambda x: len(x.get('name', '')))
                best_match = matches[0]
                self.logger.debug(f"Found project (partial match): '{best_match.get('name')}' (ID: {best_match.get('id')})")
                return best_match
                
        except Exception as e:
            self.logger.error(f"Failed to fetch projects: {e}", exc_info=True)
        
        self.logger.debug(f"Project not found: '{name}'")
        return None
    
    async def fetch_task_data(self, task_id: str) -> Optional[Dict[str, Any]]:
        """
        Fetch task data by task_id
        
        Args:
            task_id: Task ID
            
        Returns:
            Task data or None if not found
        """
        self.logger.debug(f"Fetching task data: {task_id}")
        
        # First, try cache
        task_data = self.cache.get_task_data(task_id)
        if task_data:
            result = {
                "id": task_id,
                "title": task_data.get("title", ""),
                "projectId": task_data.get("project_id"),
                "status": 0 if task_data.get("status") == "active" else 2,
                "tags": task_data.get("tags", []),
                "content": task_data.get("notes", ""),
                "reminders": task_data.get("reminders", []),
                "repeatFlag": task_data.get("repeat_flag"),
            }
            self.logger.debug(f"Found task data in cache: {task_id}")
            return result
        
        # If not in cache, try API (requires project_id)
        try:
            # Try to get project_id from cache
            cached_task = self.cache.get_task_data(task_id)
            project_id = cached_task.get('project_id') if cached_task else None
            
            if project_id:
                # Ensure client is authenticated
                if not self.client.access_token:
                    await self.client.authenticate()
                
                task = await self.client.get(
                    endpoint=f"/open/v1/project/{project_id}/task/{task_id}",
                    headers=self.client._get_headers(),
                )
                if isinstance(task, dict):
                    self.logger.debug(f"Found task data in API: {task_id}")
                    return task
        except Exception as e:
            self.logger.warning(f"Failed to fetch task data from API: {e}")
        
        self.logger.debug(f"Task data not found: {task_id}")
        return None
    
    async def fetch_projects(self) -> List[Dict[str, Any]]:
        """
        Fetch all projects
        
        Returns:
            List of projects
        """
        self.logger.debug("Fetching all projects")
        
        try:
            projects = await self.client.get_projects()
            self.logger.debug(f"Fetched {len(projects)} projects")
            return projects
        except Exception as e:
            self.logger.error(f"Failed to fetch projects: {e}", exc_info=True)
            return []
    
    async def fetch_tasks(
        self, 
        project_id: Optional[str] = None, 
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Fetch tasks with optional filters
        
        Args:
            project_id: Project ID (optional)
            filters: Additional filters (status, start_date, end_date)
            
        Returns:
            List of tasks
        """
        self.logger.debug(f"Fetching tasks (project_id: {project_id}, filters: {filters})")
        
        try:
            tasks = await self.client.get_tasks(
                project_id=project_id,
                status=filters.get("status") if filters else None,
                start_date=filters.get("start_date") if filters else None,
                end_date=filters.get("end_date") if filters else None,
            )
            self.logger.debug(f"Fetched {len(tasks)} tasks")
            return tasks
        except Exception as e:
            self.logger.error(f"Failed to fetch tasks: {e}", exc_info=True)
            return []
    
    def _format_error_message(self, missing_data: Dict[str, List[str]]) -> str:
        """
        Format error message for missing data
        
        Args:
            missing_data: Dictionary with lists of missing items by type
            
        Returns:
            Formatted error message
        """
        errors = []
        
        if missing_data.get("tasks"):
            task_names = ", ".join([f"'{t}'" for t in missing_data["tasks"]])
            errors.append(f"Задачи не найдены: {task_names}")
        
        if missing_data.get("projects"):
            project_names = ", ".join([f"'{p}'" for p in missing_data["projects"]])
            errors.append(f"Проекты не найдены: {project_names}")
        
        if missing_data.get("task_data"):
            task_ids = ", ".join(missing_data["task_data"])
            errors.append(f"Данные задач не найдены: {task_ids}")
        
        return ". ".join(errors) + ". Попробуйте создать новую задачу или укажите правильное название."

