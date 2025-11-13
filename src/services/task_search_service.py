"""
Task search service for finding tasks by title
"""

import re
from typing import Optional, Dict, List, Any
from src.api.ticktick_client import TickTickClient
from src.services.task_cache import TaskCacheService
from src.services.project_cache_service import ProjectCacheService
from src.utils.logger import logger
from src.config.constants import TICKTICK_API_VERSION


def normalize_title(title: str) -> str:
    """
    Normalize task title for comparison
    
    Rules:
    - Convert to lowercase
    - Strip whitespace
    - Replace multiple spaces with single space
    
    Examples:
    - "Протестировать работу" → "протестировать работу"
    - "протестировать  работу" → "протестировать работу"
    - "  ПРОТЕСТИРОВАТЬ РАБОТУ  " → "протестировать работу"
    
    Args:
        title: Task title
        
    Returns:
        Normalized title
    """
    if not title:
        return ""
    return re.sub(r'\s+', ' ', title.lower().strip())


class TaskSearchService:
    """Service for searching tasks by title with normalization and caching"""
    
    def __init__(
        self,
        ticktick_client: TickTickClient,
        task_cache: TaskCacheService,
        project_cache: ProjectCacheService,
    ):
        """
        Initialize task search service
        
        Args:
            ticktick_client: TickTick API client
            task_cache: Task cache service
            project_cache: Project cache service
        """
        self.client = ticktick_client
        self.cache = task_cache
        self.project_cache = project_cache
        self.logger = logger
    
    async def find_task_by_title(
        self,
        title: str,
        project_id: Optional[str] = None,
        use_cache: bool = True,
        use_api: bool = True,
    ) -> Optional[Dict[str, Any]]:
        """
        Find task by title
        
        Algorithm:
        1. Normalize title for search
        2. If use_cache=True: search in cache
        3. If not found and use_api=True:
           - If project_id specified: search only in this project
           - If project_id not specified: search in all projects
        4. On finding: save to cache
        5. Return found task or None
        
        Args:
            title: Task title to search
            project_id: Optional project ID to limit search
            use_cache: Whether to search in cache
            use_api: Whether to search in API if not found in cache
            
        Returns:
            Task data dictionary or None if not found
        """
        if not title:
            return None
        
        # Normalize title for search
        search_title_normalized = normalize_title(title)
        self.logger.info(
            f"[TaskSearch] ===== STARTING SEARCH ====="
        )
        self.logger.info(
            f"[TaskSearch] Original title: '{title}'"
        )
        self.logger.info(
            f"[TaskSearch] Normalized title: '{search_title_normalized}'"
        )
        self.logger.info(
            f"[TaskSearch] Project ID: {project_id}"
        )
        self.logger.info(
            f"[TaskSearch] Use cache: {use_cache}, Use API: {use_api}"
        )
        
        # Step 1: Search in cache
        if use_cache:
            self.logger.info(f"[TaskSearch] Step 1: Searching in cache...")
            task_id = self.cache.get_task_id_by_title(title, project_id)
            if task_id:
                task_data = self.cache.get_task_data(task_id)
                if task_data:
                    cached_title = task_data.get('title', '')
                    self.logger.info(
                        f"[TaskSearch] ✓ Found task in cache: {task_id} "
                        f"(title: '{cached_title}', normalized: '{normalize_title(cached_title)}')"
                    )
                    # Convert cache format to API format
                    return self._cache_to_api_format(task_id, task_data)
            else:
                self.logger.info(f"[TaskSearch] ✗ Task not found in cache")
        else:
            self.logger.info(f"[TaskSearch] Step 1: Cache search skipped (use_cache=False)")
        
        # Step 2: Search in API
        if not use_api:
            self.logger.info("[TaskSearch] API search disabled, returning None")
            self.logger.warning(f"[TaskSearch] ===== SEARCH FAILED (API disabled) =====")
            return None
        
        if project_id:
            # Search only in specified project
            return await self._search_in_project(project_id, search_title_normalized, title)
        else:
            # Search in all projects
            return await self._search_in_all_projects(search_title_normalized, title)
    
    async def find_task_id_by_title(
        self,
        title: str,
        project_id: Optional[str] = None,
    ) -> Optional[str]:
        """
        Find task ID by title (convenience method)
        
        Args:
            title: Task title to search
            project_id: Optional project ID to limit search
            
        Returns:
            Task ID or None if not found
        """
        task = await self.find_task_by_title(title, project_id)
        return task.get("id") if task else None
    
    async def _search_in_project(
        self,
        project_id: str,
        search_title_normalized: str,
        original_title: str,
    ) -> Optional[Dict[str, Any]]:
        """
        Search task in specific project
        
        Args:
            project_id: Project ID
            search_title_normalized: Normalized search title
            original_title: Original search title (for logging)
            
        Returns:
            Task data or None
        """
        try:
            # Ensure client is authenticated
            if not self.client.access_token:
                await self.client.authenticate()
            
            # GET /open/v1/project/{projectId}/data
            response = await self.client.get(
                endpoint=f"/open/{TICKTICK_API_VERSION}/project/{project_id}/data",
                headers=self.client._get_headers(),
            )
            
            if not isinstance(response, dict) or "tasks" not in response:
                self.logger.warning(f"[TaskSearch] Invalid response from project {project_id}")
                return None
            
            tasks = response.get("tasks", [])
            if not isinstance(tasks, list):
                self.logger.warning(f"[TaskSearch] Invalid tasks format in response for project {project_id}")
                return None
            
            self.logger.info(f"[TaskSearch] Retrieved {len(tasks)} tasks from project {project_id}")
            
            # Log all task titles for debugging
            if tasks:
                all_titles = [t.get("title", "") for t in tasks]
                self.logger.info(f"[TaskSearch] All task titles from API: {all_titles}")
                normalized_titles = [normalize_title(t) for t in all_titles]
                self.logger.info(f"[TaskSearch] Normalized task titles: {normalized_titles}")
            
            # Try exact match first
            self.logger.info(f"[TaskSearch] Trying exact match...")
            matching_task = self._find_exact_match(tasks, search_title_normalized)
            
            # If not found, try partial match
            if not matching_task:
                self.logger.info(f"[TaskSearch] Exact match not found, trying partial match...")
                matching_task = self._find_partial_match(tasks, search_title_normalized)
            
            # If found, save to cache and return
            if matching_task:
                self._save_to_cache(matching_task)
                self.logger.info(
                    f"[TaskSearch] ✓ Found task in project {project_id}: "
                    f"{matching_task.get('id')} ('{matching_task.get('title')}')"
                )
                self.logger.info(f"[TaskSearch] ===== SEARCH SUCCESS =====")
                return matching_task
            
            # Check completed tasks from cache for this project
            self.logger.info(f"[TaskSearch] Checking completed tasks from cache...")
            completed_task = await self._check_completed_tasks(project_id, search_title_normalized)
            if completed_task:
                self.logger.info(f"[TaskSearch] ===== SEARCH SUCCESS (completed task) =====")
                return completed_task
            
            self.logger.warning(
                f"[TaskSearch] ===== SEARCH FAILED ====="
            )
            self.logger.warning(
                f"[TaskSearch] Task '{original_title}' (normalized: '{search_title_normalized}') "
                f"not found in project {project_id}"
            )
            return None
            
        except Exception as e:
            self.logger.error(f"[TaskSearch] Error searching in project {project_id}: {e}", exc_info=True)
            return None
    
    async def _search_in_all_projects(
        self,
        search_title_normalized: str,
        original_title: str,
    ) -> Optional[Dict[str, Any]]:
        """
        Search task in all projects
        
        Args:
            search_title_normalized: Normalized search title
            original_title: Original search title (for logging)
            
        Returns:
            Task data or None
        """
        try:
            # Get list of projects (from cache or API)
            projects = await self.project_cache.get_projects()
            
            if not projects:
                self.logger.warning("[TaskSearch] No projects available for search")
                return None
            
            self.logger.debug(f"[TaskSearch] Searching in {len(projects)} projects")
            
            # Search in each project
            for project in projects:
                project_id = project.get("id")
                if not project_id:
                    continue
                
                matching_task = await self._search_in_project(
                    project_id,
                    search_title_normalized,
                    original_title,
                )
                
                if matching_task:
                    # Found! Stop searching
                    return matching_task
            
            # Not found in any project
            self.logger.warning(
                f"[TaskSearch] ===== SEARCH FAILED ====="
            )
            self.logger.warning(
                f"[TaskSearch] Task '{original_title}' (normalized: '{search_title_normalized}') "
                f"not found in any of {len(projects)} projects"
            )
            return None
            
        except Exception as e:
            self.logger.error(f"[TaskSearch] Error searching in all projects: {e}", exc_info=True)
            return None
    
    def _find_exact_match(
        self,
        tasks: List[Dict[str, Any]],
        search_title_normalized: str,
    ) -> Optional[Dict[str, Any]]:
        """
        Find exact match in tasks list
        
        Args:
            tasks: List of tasks
            search_title_normalized: Normalized search title
            
        Returns:
            Matching task or None
        """
        for task in tasks:
            task_title = task.get("title", "")
            task_title_normalized = normalize_title(task_title)
            
            self.logger.debug(
                f"[TaskSearch] Comparing: '{task_title}' (normalized: '{task_title_normalized}') "
                f"== '{search_title_normalized}'"
            )
            
            if task_title_normalized == search_title_normalized:
                self.logger.info(f"[TaskSearch] ✓ Exact match found: '{task_title}'")
                return task
        
        self.logger.info(f"[TaskSearch] ✗ Exact match not found")
        return None
    
    def _find_partial_match(
        self,
        tasks: List[Dict[str, Any]],
        search_title_normalized: str,
    ) -> Optional[Dict[str, Any]]:
        """
        Find partial match in tasks list
        
        Args:
            tasks: List of tasks
            search_title_normalized: Normalized search title
            
        Returns:
            Best matching task or None
        """
        matches = []
        
        self.logger.info(f"[TaskSearch] Checking partial matches...")
        for task in tasks:
            task_title = task.get("title", "")
            task_title_normalized = normalize_title(task_title)
            
            # Check if search title is contained in task title or vice versa
            contains_search = search_title_normalized in task_title_normalized
            contains_task = task_title_normalized in search_title_normalized
            
            self.logger.debug(
                f"[TaskSearch] Partial check: '{task_title}' (normalized: '{task_title_normalized}') "
                f"- search in task: {contains_search}, task in search: {contains_task}"
            )
            
            if contains_search or contains_task:
                matches.append((task, len(task_title_normalized), task_title))
                self.logger.debug(f"[TaskSearch] Partial match candidate: '{task_title}'")
        
        if matches:
            # Prefer longer match (more specific)
            matches.sort(key=lambda x: x[1], reverse=True)
            best_match = matches[0]
            
            self.logger.info(
                f"[TaskSearch] ✓ Partial match found: '{best_match[2]}' "
                f"(normalized: '{normalize_title(best_match[2])}') "
                f"for search '{search_title_normalized}'"
            )
            
            if len(matches) > 1:
                self.logger.warning(
                    f"[TaskSearch] Multiple partial matches found ({len(matches)}): "
                    f"{[m[2] for m in matches]}, using '{best_match[2]}'"
                )
            
            return best_match[0]
        
        self.logger.info(f"[TaskSearch] ✗ Partial match not found")
        return None
    
    def _save_to_cache(self, task: Dict[str, Any]) -> None:
        """
        Save task to cache
        
        Args:
            task: Task data from API
        """
        try:
            task_id = task.get("id")
            if not task_id:
                return
            
            # Convert API status to cache status
            api_status = task.get("status", 0)
            cache_status = "completed" if api_status == 2 else "active"
            
            self.cache.save_task(
                task_id=task_id,
                title=task.get("title", ""),
                project_id=task.get("projectId"),
                status=cache_status,
                tags=task.get("tags", []),
                notes=task.get("content", ""),
                reminders=task.get("reminders", []),
                repeat_flag=task.get("repeatFlag"),
            )
            self.logger.debug(f"[TaskSearch] Saved task {task_id} to cache")
        except Exception as e:
            self.logger.warning(f"[TaskSearch] Failed to save task to cache: {e}", exc_info=True)
    
    def _cache_to_api_format(
        self,
        task_id: str,
        task_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Convert cache format to API format
        
        Args:
            task_id: Task ID
            task_data: Task data from cache
            
        Returns:
            Task data in API format
        """
        # Convert cache status to API status
        cache_status = task_data.get("status", "active")
        api_status = 2 if cache_status == "completed" else 0
        
        return {
            "id": task_id,
            "title": task_data.get("title", ""),
            "projectId": task_data.get("project_id"),
            "status": api_status,
            "tags": task_data.get("tags", []),
            "content": task_data.get("notes", ""),
            "reminders": task_data.get("reminders", []),
            "repeatFlag": task_data.get("repeat_flag"),
        }
    
    async def _check_completed_tasks(
        self,
        project_id: str,
        search_title_normalized: str,
    ) -> Optional[Dict[str, Any]]:
        """
        Check completed tasks from cache for this project
        
        GET /project/{projectId}/data returns only incomplete tasks (status=0).
        For completed tasks, we need to check cache.
        
        Args:
            project_id: Project ID
            search_title_normalized: Normalized search title
            
        Returns:
            Task data or None
        """
        try:
            # Get completed tasks from cache for this project
            completed_tasks = self.cache.get_completed_tasks(project_id=project_id)
            
            if not completed_tasks:
                return None
            
            self.logger.debug(
                f"[TaskSearch] Checking {len(completed_tasks)} completed tasks from cache "
                f"for project {project_id}"
            )
            
            # Search in completed tasks
            for task_id, task_project_id in completed_tasks:
                if task_project_id != project_id:
                    continue
                
                task_data = self.cache.get_task_data(task_id)
                if not task_data:
                    continue
                
                task_title_normalized = normalize_title(task_data.get("title", ""))
                if task_title_normalized == search_title_normalized:
                    # Found completed task!
                    self.logger.info(
                        f"[TaskSearch] Found completed task in cache: {task_id} "
                        f"('{task_data.get('title')}')"
                    )
                    return self._cache_to_api_format(task_id, task_data)
            
            return None
            
        except Exception as e:
            self.logger.warning(
                f"[TaskSearch] Error checking completed tasks: {e}",
                exc_info=True,
            )
            return None

