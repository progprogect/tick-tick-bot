"""
Data fetcher service for retrieving data from cache and API
"""

import re
from typing import Optional, Dict, List, Any
from src.api.ticktick_client import TickTickClient
from src.services.task_cache import TaskCacheService
from src.utils.logger import logger


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
        self.logger = logger
    
    async def fetch_data_requirements(self, requirements: Dict[str, Any]) -> Dict[str, Any]:
        """
        Fetch data based on requirements from GPT
        
        Args:
            requirements: Dictionary with required_data structure from GPT
            
        Returns:
            Dictionary with fetched data
        """
        self.logger.debug(f"Fetching data requirements: {requirements}")
        
        fetched_data = {
            "tasks": {},
            "projects": {},
            "task_data": {},
            "current_task_data": {},
        }
        
        required_data = requirements.get("required_data", {})
        
        # Fetch tasks by title
        task_titles = required_data.get("task_by_title", [])
        for title in task_titles:
            project_id = required_data.get("project_by_name_for_task", {}).get(title)
            task = await self.fetch_task_by_title(title, project_id)
            if task:
                fetched_data["tasks"][title] = task
            else:
                fetched_data["tasks"][title] = None
        
        # Fetch projects by name
        project_names = required_data.get("project_by_name", [])
        for name in project_names:
            project = await self.fetch_project_by_name(name)
            if project:
                fetched_data["projects"][name] = project
            else:
                fetched_data["projects"][name] = None
        
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
        
        self.logger.debug(f"Fetched data: {len(fetched_data.get('tasks', {}))} tasks, "
                         f"{len(fetched_data.get('projects', {}))} projects")
        
        return fetched_data
    
    async def fetch_task_by_title(
        self, 
        title: str, 
        project_id: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Fetch task by title (searches in cache first, then API)
        
        Args:
            title: Task title
            project_id: Project ID (optional)
            
        Returns:
            Task data or None if not found
        """
        self.logger.debug(f"Fetching task by title: '{title}' (project_id: {project_id})")
        
        # First, try cache
        task_id = self.cache.get_task_id_by_title(title, project_id)
        if task_id:
            task_data = self.cache.get_task_data(task_id)
            if task_data:
                # Return structured data similar to API response
                result = {
                    "id": task_id,
                    "title": task_data.get("title", title),
                    "projectId": task_data.get("project_id"),
                    "status": 0 if task_data.get("status") == "active" else 2,
                    "tags": task_data.get("tags", []),
                    "content": task_data.get("notes", ""),
                    "reminders": task_data.get("reminders", []),
                    "repeatFlag": task_data.get("repeat_flag"),
                }
                self.logger.debug(f"Found task in cache: {task_id}")
                return result
        
        # If not in cache, try API (may fail, but try anyway)
        try:
            tasks = await self.client.get_tasks(project_id=project_id)
            matching_task = next(
                (t for t in tasks if t.get("title", "").lower() == title.lower()),
                None
            )
            
            if matching_task:
                task_id = matching_task.get("id")
                # Cache it for future use
                self.cache.save_task(
                    task_id=task_id,
                    title=title,
                    project_id=matching_task.get("projectId") or project_id,
                )
                self.logger.debug(f"Found task in API: {task_id}")
                return matching_task
        except Exception as e:
            self.logger.warning(f"Failed to search task in API: {e}")
        
        self.logger.debug(f"Task not found: '{title}'")
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

