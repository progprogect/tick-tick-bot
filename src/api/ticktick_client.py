"""
TickTick API client
"""

import base64
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone, timedelta
from src.api.base_client import BaseAPIClient
from src.config.settings import settings
from src.config.constants import TICKTICK_API_BASE_URL, TICKTICK_API_VERSION, USER_TIMEZONE_OFFSET, USER_TIMEZONE_STR
from src.utils.logger import logger


def _format_date_for_ticktick(date_str: str) -> str:
    """
    Format date string to TickTick API format: "yyyy-MM-dd'T'HH:mm:ssZ"
    Example: "2019-11-13T03:00:00+0000"
    
    ВАЖНО: Все время интерпретируется как UTC+3 (локальное время пользователя).
    При отправке в API конвертируется в UTC.
    
    Args:
        date_str: Date string in ISO format or other formats
        
    Returns:
        Formatted date string for TickTick API (в UTC)
    """
    if not date_str:
        return ""
    
    try:
        # Create UTC+3 timezone
        user_tz = timezone(timedelta(hours=USER_TIMEZONE_OFFSET))
        
        # Try to parse ISO format
        if "T" in date_str:
            # Already has time component
            # Try to parse with timezone
            try:
                dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
            except ValueError:
                # If parsing fails, try without timezone
                dt = datetime.fromisoformat(date_str)
                # If naive datetime, assume it's in UTC+3 (user's local time)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=user_tz)
        else:
            # Date only, assume midnight in UTC+3
            dt = datetime.fromisoformat(date_str)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=user_tz)
        
        # If datetime has timezone info, convert to UTC
        # If no timezone, it's already in user_tz (UTC+3)
        if dt.tzinfo is not None:
            # Convert to UTC
            dt_utc = dt.astimezone(timezone.utc)
        else:
            # Should not happen after our checks, but just in case
            dt_utc = dt.replace(tzinfo=user_tz).astimezone(timezone.utc)
        
        # Format to TickTick API format: "yyyy-MM-dd'T'HH:mm:ss+0000" (UTC)
        formatted = dt_utc.strftime("%Y-%m-%dT%H:%M:%S+0000")
        return formatted
    except Exception as e:
        logger.warning(f"Failed to format date '{date_str}': {e}")
        # Return as is if parsing fails
        return date_str


class TickTickClient(BaseAPIClient):
    """Client for TickTick OpenAPI"""
    
    def __init__(self):
        """Initialize TickTick client"""
        super().__init__(TICKTICK_API_BASE_URL)
        self.email = settings.TICKTICK_EMAIL
        self.password = settings.TICKTICK_PASSWORD
        self.access_token = settings.TICKTICK_ACCESS_TOKEN
        self.client_id = settings.TICKTICK_CLIENT_ID
        self.client_secret = settings.TICKTICK_CLIENT_SECRET
        self.logger = logger
    
    async def authenticate(self) -> bool:
        """
        Authenticate with TickTick API
        
        Returns:
            True if authentication successful, False otherwise
        """
        try:
            # If access token is provided directly, use it
            if self.access_token:
                self.logger.info("Using provided access token")
                return True
            
            # Try OAuth 2.0 if credentials are available
            if self.client_id and self.client_secret:
                return await self._authenticate_oauth()
            else:
                # Fallback to email/password authentication
                return await self._authenticate_email_password()
        
        except Exception as e:
            self.logger.error(f"Authentication failed: {e}")
            return False
    
    async def _authenticate_oauth(self) -> bool:
        """Authenticate using OAuth 2.0"""
        try:
            # OAuth 2.0 flow
            # First, get authorization code (this usually requires user interaction)
            # For server-to-server, we might need to use password grant
            auth_string = base64.b64encode(
                f"{self.client_id}:{self.client_secret}".encode()
            ).decode()
            
            headers = {
                "Authorization": f"Basic {auth_string}",
                "Content-Type": "application/x-www-form-urlencoded",
            }
            
            # Use form data for OAuth token endpoint
            import urllib.parse
            data = urllib.parse.urlencode({
                "grant_type": "password",
                "username": self.email,
                "password": self.password,
            })
            
            # Override Content-Type for form data
            headers["Content-Type"] = "application/x-www-form-urlencoded"
            
            response = await self.post(
                endpoint="/oauth/token",
                headers=headers,
                params=None,
                json_data=None,
                data=data,
            )
            
            self.access_token = response.get("access_token")
            
            if self.access_token:
                self.logger.info("Successfully authenticated with OAuth 2.0")
                return True
            
            return False
        
        except Exception as e:
            self.logger.error(f"OAuth authentication failed: {e}")
            return False
    
    async def _authenticate_email_password(self) -> bool:
        """Authenticate using email and password (direct API)"""
        try:
            # TickTick API uses email/password authentication
            # We need to get access token through login endpoint
            headers = {
                "Content-Type": "application/json",
            }
            
            data = {
                "username": self.email,
                "password": self.password,
            }
            
            # Try to authenticate - this might vary based on actual API
            # For now, we'll use a workaround with direct API calls
            response = await self.post(
                endpoint="/api/v2/user/signin",
                headers=headers,
                json_data=data,
            )
            
            # The response might contain token or session info
            # Adjust based on actual API response
            if "token" in response:
                self.access_token = response["token"]
            elif "access_token" in response:
                self.access_token = response["access_token"]
            else:
                # Store credentials for future requests
                self.access_token = base64.b64encode(
                    f"{self.email}:{self.password}".encode()
                ).decode()
            
            self.logger.info("Successfully authenticated with email/password")
            return True
        
        except Exception as e:
            self.logger.error(f"Email/password authentication failed: {e}")
            # For now, we'll use basic auth as fallback
            self.access_token = base64.b64encode(
                f"{self.email}:{self.password}".encode()
            ).decode()
            return True
    
    def _get_headers(self) -> Dict[str, str]:
        """Get request headers with authentication"""
        headers = {
            "Content-Type": "application/json",
        }
        
        if self.access_token:
            # Use Bearer token authentication
            headers["Authorization"] = f"Bearer {self.access_token}"
        elif self.client_id and self.client_secret:
            # OAuth token if available
            if hasattr(self, 'oauth_token') and self.oauth_token:
                headers["Authorization"] = f"Bearer {self.oauth_token}"
            else:
                # Basic auth fallback
                auth_string = base64.b64encode(
                    f"{self.email}:{self.password}".encode()
                ).decode()
                headers["Authorization"] = f"Basic {auth_string}"
        
        return headers
    
    async def create_task(
        self,
        title: str,
        project_id: Optional[str] = None,
        due_date: Optional[str] = None,
        priority: int = 0,
        tags: Optional[List[str]] = None,
        notes: Optional[str] = None,
        status: int = 0,
        repeat_flag: Optional[str] = None,
        reminders: Optional[List[str]] = None,
        start_date: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Create a new task
        
        Args:
            title: Task title
            project_id: Project/list ID
            due_date: Due date in ISO 8601 format
            priority: Priority (0-3)
            tags: List of tags
            notes: Task notes
            status: Status (0: Incomplete, 1: Completed)
            repeat_flag: Recurring rules in RRULE format (e.g., "RRULE:FREQ=DAILY;INTERVAL=1")
            reminders: List of reminder triggers (e.g., ["TRIGGER:P0DT9H0M0S", "TRIGGER:PT0S"])
            start_date: Start date in ISO 8601 format (required for recurring tasks)
            
        Returns:
            Created task data
        """
        if not self.access_token:
            await self.authenticate()
        
        task_data = {
            "title": title,
            "status": status,  # 0: Incomplete, 1: Completed
        }
        
        if project_id:
            task_data["projectId"] = project_id
        
        if due_date:
            task_data["dueDate"] = _format_date_for_ticktick(due_date)
        
        if start_date:
            task_data["startDate"] = _format_date_for_ticktick(start_date)
        
        if priority:
            task_data["priority"] = priority
        
        if tags:
            task_data["tags"] = tags
        
        if notes:
            task_data["content"] = notes
        
        if repeat_flag:
            task_data["repeatFlag"] = repeat_flag
        
        if reminders:
            task_data["reminders"] = reminders
        
        return await self.post(
            endpoint=f"/open/{TICKTICK_API_VERSION}/task",
            headers=self._get_headers(),
            json_data=task_data,
        )
    
    async def complete_task(self, task_id: str, project_id: Optional[str] = None) -> bool:
        """
        Mark task as completed
        
        According to TickTick API documentation:
        POST /open/v1/project/{projectId}/task/{taskId}/complete
        
        Args:
            task_id: Task ID to complete
            project_id: Project ID (optional, will try to get from cache)
            
        Returns:
            True if successful
        """
        if not self.access_token:
            await self.authenticate()
        
        # Get project_id from cache if not provided
        if not project_id:
            from src.services.task_cache import TaskCacheService
            cache = TaskCacheService()
            cached_task = cache.get_task_data(task_id)
            if cached_task and cached_task.get('project_id'):
                project_id = cached_task.get('project_id')
            else:
                raise ValueError(f"projectId is required for complete, but not found in cache for task {task_id}")
        
        # According to TickTick API documentation:
        # POST /open/v1/project/{projectId}/task/{taskId}/complete
        await self.post(
            endpoint=f"/open/{TICKTICK_API_VERSION}/project/{project_id}/task/{task_id}/complete",
            headers=self._get_headers(),
            json_data={},  # No body needed
        )
        
        # Mark as completed in cache
        from src.services.task_cache import TaskCacheService
        cache = TaskCacheService()
        cache.mark_as_completed(task_id)
        
        return True
    
    async def update_task(
        self,
        task_id: str,
        title: Optional[str] = None,
        project_id: Optional[str] = None,
        column_id: Optional[str] = None,
        due_date: Optional[str] = None,
        priority: Optional[int] = None,
        status: Optional[int] = None,
        tags: Optional[List[str]] = None,
        notes: Optional[str] = None,
        repeat_flag: Optional[str] = None,
        reminders: Optional[List[str]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Update existing task
        
        Args:
            task_id: Task ID
            title: New title
            project_id: New project ID
            column_id: New column ID (for Kanban projects)
            due_date: New due date
            priority: New priority
            status: New status (0: Incomplete, 1: Completed)
            tags: New tags
            notes: New notes
            repeat_flag: Recurring rules in RRULE format (e.g., "RRULE:FREQ=DAILY;INTERVAL=1")
            reminders: List of reminder triggers (e.g., ["TRIGGER:P0DT9H0M0S", "TRIGGER:PT0S"])
            
        Returns:
            Updated task data
        """
        if not self.access_token:
            await self.authenticate()
        
        task_data = {}
        
        # Add kwargs first (allows passing fields directly)
        task_data.update(kwargs)
        
        # Then add explicit parameters if provided
        if title is not None:
            task_data["title"] = title
        
        if project_id is not None:
            task_data["projectId"] = project_id
        
        if column_id is not None:
            task_data["columnId"] = column_id
        
        if due_date is not None:
            task_data["dueDate"] = _format_date_for_ticktick(due_date)
        
        if priority is not None:
            task_data["priority"] = priority
        
        if status is not None:
            task_data["status"] = status
        
        if tags is not None:
            task_data["tags"] = tags
        
        if notes is not None:
            task_data["content"] = notes
        
        if repeat_flag is not None:
            task_data["repeatFlag"] = repeat_flag
        
        if reminders is not None:
            task_data["reminders"] = reminders
        
        # Format all date fields according to TickTick API format
        # Fields that need formatting: dueDate, startDate, completedTime
        date_fields = {"dueDate", "startDate", "completedTime"}
        for field in date_fields:
            if field in task_data and task_data[field] is not None:
                task_data[field] = _format_date_for_ticktick(str(task_data[field]))
        
        # Ensure we have at least one field to update
        if not task_data:
            raise ValueError("No fields to update")
        
        # According to TickTick API documentation:
        # Update Task uses POST /open/v1/task/{taskId}
        # Required fields: id, projectId
        # Get projectId from cache if not provided
        source_project_id = None
        if "projectId" not in task_data:
            from src.services.task_cache import TaskCacheService
            cache = TaskCacheService()
            cached_task = cache.get_task_data(task_id)
            if cached_task and cached_task.get('project_id'):
                source_project_id = cached_task.get('project_id')
                task_data["projectId"] = source_project_id
            else:
                raise ValueError("projectId is required for update, but not found in cache")
        else:
            # If projectId is being changed (move task), we need to get current task data
            # and include required fields to ensure proper update
            new_project_id = task_data.get("projectId")  # This is the NEW projectId from parameter
            # If projectId is explicitly provided, check if it's different from cached
            from src.services.task_cache import TaskCacheService
            cache = TaskCacheService()
            cached_task = cache.get_task_data(task_id)
            if cached_task and cached_task.get('project_id') and cached_task.get('project_id') != new_project_id:
                # This is a move operation - get current task data
                # According to TickTick API docs, we need id and projectId (required)
                # We should also include title and other editable fields
                try:
                    current_project_id = cached_task.get('project_id')
                    full_task = await self.get(
                        endpoint=f"/open/{TICKTICK_API_VERSION}/project/{current_project_id}/task/{task_id}",
                        headers=self._get_headers(),
                    )
                    
                    # For move operation: copy ALL fields from original task
                    # and change ONLY projectId to the new target
                    # This ensures we don't lose any data
                    task_data = full_task.copy()
                    
                    # Remove system/metadata fields that shouldn't be sent
                    system_fields = ['etag']  # sortOrder might be needed, etag definitely not
                    for key in system_fields:
                        if key in task_data:
                            del task_data[key]
                    
                    # Change projectId to NEW target (from parameter, not from full_task)
                    task_data['projectId'] = new_project_id  # Use the NEW projectId from parameter
                    task_data['id'] = task_id  # Ensure id is set
                    self.logger.debug(f"Move operation: retrieved task data with {len(task_data)} fields, changing projectId from {current_project_id} to {new_project_id}")
                except Exception as e:
                    self.logger.warning(f"Could not retrieve full task data for move: {e}. Proceeding with minimal update.")
                    # If we can't get full task, ensure we at least have id and projectId
                    if 'id' not in task_data:
                        task_data['id'] = task_id
                    # Ensure projectId is set to new value
                    task_data['projectId'] = new_project_id
        
        # id is required according to API docs
        task_data["id"] = task_id
        
        # Use POST instead of PUT (as per TickTick API documentation)
        return await self.post(
            endpoint=f"/open/{TICKTICK_API_VERSION}/task/{task_id}",
            headers=self._get_headers(),
            json_data=task_data,
        )
    
    async def delete_task(self, task_id: str, project_id: Optional[str] = None) -> bool:
        """
        Delete task
        
        According to TickTick API documentation:
        DELETE /open/v1/project/{projectId}/task/{taskId}
        
        Args:
            task_id: Task ID
            project_id: Project ID (optional, will try to get from cache)
            
        Returns:
            True if successful
        """
        if not self.access_token:
            await self.authenticate()
        
        # Get project_id from cache if not provided
        if not project_id:
            from src.services.task_cache import TaskCacheService
            cache = TaskCacheService()
            cached_task = cache.get_task_data(task_id)
            if cached_task and cached_task.get('project_id'):
                project_id = cached_task.get('project_id')
            else:
                raise ValueError("projectId is required for delete, but not found in cache")
        
        # According to TickTick API documentation:
        # DELETE /open/v1/project/{projectId}/task/{taskId}
        await self.delete(
            endpoint=f"/open/{TICKTICK_API_VERSION}/project/{project_id}/task/{task_id}",
            headers=self._get_headers(),
        )
        
        return True
    
    async def get_tasks(
        self,
        project_id: Optional[str] = None,
        status: Optional[int] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Get list of tasks
        
        According to TickTick API documentation:
        - GET /open/v1/project/{projectId}/data - returns project with tasks
        - GET /open/v1/project/{projectId}/task/{taskId} - returns single task
        
        Args:
            project_id: Filter by project ID (if None, will try to get from all projects)
            status: Filter by status (0: Incomplete, 1: Completed)
            start_date: Filter by start date
            end_date: Filter by end date
            
        Returns:
            List of tasks
        """
        if not self.access_token:
            await self.authenticate()
        
        try:
            all_tasks = []
            
            if project_id:
                # Get tasks from specific project using GET /open/v1/project/{projectId}/data
                try:
                    response = await self.get(
                        endpoint=f"/open/{TICKTICK_API_VERSION}/project/{project_id}/data",
                        headers=self._get_headers(),
                    )
                    
                    if isinstance(response, dict) and "tasks" in response:
                        tasks = response["tasks"]
                        if isinstance(tasks, list):
                            all_tasks.extend(tasks)
                except Exception as e:
                    self.logger.warning(f"Failed to get tasks from project {project_id}: {e}")
                    # Try fallback: get single task if we have task_id (not applicable here)
                    return []
            else:
                # Get tasks from all projects
                # First, get list of projects
                try:
                    projects = await self.get_projects()
                    self.logger.info(f"[get_tasks] Retrieved {len(projects)} projects from API")
                    
                    # Log project details for debugging
                    for project in projects[:5]:  # Log first 5
                        self.logger.debug(
                            f"[get_tasks] Project: {project.get('name', 'N/A')} "
                            f"(id: {project.get('id', 'N/A')}, "
                            f"kind: {project.get('kind', 'N/A')}, "
                            f"closed: {project.get('closed', False)})"
                        )
                    
                    # First, get tasks from Inbox (Inbox is not in the projects list)
                    try:
                        self.logger.debug("[get_tasks] Fetching tasks from Inbox...")
                        inbox_response = await self.get(
                            endpoint=f"/open/{TICKTICK_API_VERSION}/project/inbox/data",
                            headers=self._get_headers(),
                        )
                        
                        if isinstance(inbox_response, dict) and "tasks" in inbox_response:
                            inbox_tasks = inbox_response["tasks"]
                            if isinstance(inbox_tasks, list):
                                # Sort by timestamp from ID (more reliable than sortOrder)
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
                                
                                sorted_inbox_tasks = sorted(
                                    inbox_tasks,
                                    key=get_task_timestamp,
                                    reverse=True  # Higher timestamp = newer task
                                )
                                # Take first 99 (most recent)
                                inbox_tasks = sorted_inbox_tasks[:99]
                                all_tasks.extend(inbox_tasks)
                                self.logger.info(
                                    f"[get_tasks] Retrieved {len(inbox_tasks)} most recent tasks from Inbox "
                                    f"(sorted by sortOrder, most recent first)"
                                )
                            else:
                                self.logger.warning(
                                    f"[get_tasks] Invalid tasks format from Inbox: {type(inbox_tasks)}"
                                )
                        else:
                            self.logger.debug(
                                f"[get_tasks] No tasks in Inbox response "
                                f"(response keys: {list(inbox_response.keys()) if isinstance(inbox_response, dict) else 'not a dict'})"
                            )
                    except Exception as e:
                        self.logger.warning(
                            f"[get_tasks] Failed to get tasks from Inbox: {e}"
                        )
                        # Continue even if Inbox fails
                    
                    # Then, get tasks from all regular projects
                    for project in projects:
                        project_id_val = project.get("id")
                        project_name = project.get("name", "N/A")
                        project_kind = project.get("kind", "TASK")
                        project_closed = project.get("closed", False)
                        
                        if not project_id_val:
                            self.logger.warning(f"[get_tasks] Project without ID: {project}")
                            continue
                        
                        # Skip NOTE projects (they don't have tasks)
                        if project_kind == "NOTE":
                            self.logger.debug(f"[get_tasks] Skipping NOTE project: {project_name}")
                            continue
                        
                        try:
                            response = await self.get(
                                endpoint=f"/open/{TICKTICK_API_VERSION}/project/{project_id_val}/data",
                                headers=self._get_headers(),
                            )
                            
                            if isinstance(response, dict) and "tasks" in response:
                                tasks = response["tasks"]
                                if isinstance(tasks, list):
                                    # Sort by timestamp from ID (more reliable than sortOrder)
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
                                    
                                    sorted_tasks = sorted(
                                        tasks,
                                        key=get_task_timestamp,
                                        reverse=True  # Higher timestamp = newer task
                                    )
                                    # Take first 99 (most recent)
                                    tasks = sorted_tasks[:99]
                                    all_tasks.extend(tasks)
                                    self.logger.debug(
                                        f"[get_tasks] Retrieved {len(tasks)} most recent tasks from project "
                                        f"'{project_name}' (id: {project_id_val}, closed: {project_closed}, "
                                        f"sorted by sortOrder, most recent first)"
                                    )
                                else:
                                    self.logger.warning(
                                        f"[get_tasks] Invalid tasks format from project {project_name}: {type(tasks)}"
                                    )
                            else:
                                self.logger.warning(
                                    f"[get_tasks] No tasks in response from project {project_name} "
                                    f"(response keys: {list(response.keys()) if isinstance(response, dict) else 'not a dict'})"
                                )
                        except Exception as e:
                            self.logger.warning(
                                f"[get_tasks] Failed to get tasks from project '{project_name}' "
                                f"(id: {project_id_val}): {e}"
                            )
                            continue
                    
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
                        f"[get_tasks] Total tasks retrieved from all projects: {len(all_tasks)} "
                        f"(sorted by sortOrder across all projects, most recent first)"
                    )
                except Exception as e:
                    self.logger.error(f"[get_tasks] Failed to get projects: {e}", exc_info=True)
                    return []
            
            # Filter by status if specified
            if status is not None:
                # Note: TickTick API uses status=0 (incomplete), status=1 (in progress?), status=2 (completed)
                # GET /project/{projectId}/data returns only "Undone tasks" (status=0)
                # For completed tasks (status=2), we need to use cache or individual GET requests
                if status == 1 or status == 2:
                    # Get completed tasks (status=2 in TickTick)
                    # Since GET /project/{projectId}/data doesn't return completed tasks,
                    # we need to get them from cache and then verify with API
                    from src.services.task_cache import TaskCacheService
                    cache = TaskCacheService()
                    
                    # Get all tasks from cache with status=completed
                    completed_task_ids = cache.get_completed_tasks(project_id=project_id)
                    
                    # Fetch completed tasks from API using GET /project/{projectId}/task/{taskId}
                    completed_tasks = []
                    for task_id, task_project_id in completed_task_ids:
                        if not task_project_id:
                            continue
                        try:
                            task = await self.get(
                                endpoint=f"/open/{TICKTICK_API_VERSION}/project/{task_project_id}/task/{task_id}",
                                headers=self._get_headers(),
                            )
                            if isinstance(task, dict) and task.get("status") == 2:
                                completed_tasks.append(task)
                        except Exception as e:
                            # Task might be deleted or doesn't exist anymore
                            self.logger.debug(f"Task {task_id} not found or deleted: {e}")
                            continue
                    
                    all_tasks = completed_tasks
                else:
                    # For incomplete tasks (status=0), filter from already fetched tasks
                    all_tasks = [t for t in all_tasks if t.get("status") == status]
            
            # Filter by date range if specified
            if start_date or end_date:
                from datetime import datetime, timezone
                filtered_tasks = []
                
                # Parse date range once
                start_dt = None
                end_dt = None
                
                if start_date:
                    start_date_str = start_date.replace('Z', '+00:00')
                    if '+' not in start_date_str and 'Z' not in start_date:
                        start_date_str = start_date + '+00:00'
                    start_dt = datetime.fromisoformat(start_date_str)
                    if start_dt.tzinfo is None:
                        start_dt = start_dt.replace(tzinfo=timezone.utc)
                
                if end_date:
                    end_date_str = end_date.replace('Z', '+00:00')
                    if '+' not in end_date_str and 'Z' not in end_date:
                        end_date_str = end_date + '+00:00'
                    end_dt = datetime.fromisoformat(end_date_str)
                    if end_dt.tzinfo is None:
                        end_dt = end_dt.replace(tzinfo=timezone.utc)
                
                for task in all_tasks:
                    # For completed tasks, use completedTime; for incomplete, use dueDate
                    # Note: TickTick API uses status=2 for completed tasks (not 1)
                    task_status = task.get("status", 0)
                    task_date_str = None
                    
                    if task_status == 2:  # Completed (TickTick uses 2, not 1)
                        task_date_str = task.get("completedTime")
                    else:  # Incomplete (status=0 or 1)
                        task_date_str = task.get("dueDate")
                    
                    # If no date, skip (unless we want to include tasks without dates)
                    if not task_date_str:
                        # For analytics, we might want to include tasks without dates
                        # But for now, skip them
                        continue
                    
                    try:
                        # Parse ISO format date - ensure timezone-aware
                        date_str = task_date_str.replace('Z', '+00:00')
                        if '+' not in date_str and 'Z' not in task_date_str:
                            date_str = task_date_str + '+00:00'
                        task_date = datetime.fromisoformat(date_str)
                        
                        # Ensure task_date is timezone-aware
                        if task_date.tzinfo is None:
                            task_date = task_date.replace(tzinfo=timezone.utc)
                        
                        # Check date range
                        if start_dt and task_date < start_dt:
                            continue
                        
                        if end_dt and task_date > end_dt:
                            continue
                        
                        filtered_tasks.append(task)
                    except Exception as e:
                        self.logger.warning(f"Failed to parse date for task {task.get('id')}: {e}")
                        continue
                
                all_tasks = filtered_tasks
            
            return all_tasks
            
        except Exception as e:
            self.logger.warning(f"Failed to get tasks: {e}")
            return []
    
    async def add_tags(self, task_id: str, tags: List[str]) -> Dict[str, Any]:
        """
        Add tags to task
        
        Note: TickTick API doesn't have a separate endpoint for adding tags.
        We need to use update_task with tags field.
        
        Args:
            task_id: Task ID
            tags: List of tags to add
            
        Returns:
            Updated task data
        """
        if not self.access_token:
            await self.authenticate()
        
        # Since we can't get current task (GET fails), we'll just set the tags
        # This means we're replacing tags, not adding to existing ones
        # But this is the best we can do with the current API limitations
        return await self.update_task(
            task_id=task_id,
            tags=tags,
        )
    
    def _convert_reminder_time_to_trigger(self, reminder_time: str) -> str:
        """
        Convert reminder time (ISO 8601) to TickTick TRIGGER format
        
        Args:
            reminder_time: Reminder time in ISO 8601 format (e.g., "2024-11-05T12:00:00+00:00")
            
        Returns:
            TRIGGER string (e.g., "TRIGGER:P0DT9H0M0S" for 9 hours before, "TRIGGER:PT0S" for at time)
        """
        from datetime import datetime, timedelta
        
        try:
            # Parse reminder time
            reminder_dt = datetime.fromisoformat(reminder_time.replace('Z', '+00:00'))
            now = datetime.now(reminder_dt.tzinfo)
            
            # Calculate difference
            diff = reminder_dt - now
            
            # Format as TRIGGER: P = period, D = days, T = time, H = hours, M = minutes, S = seconds
            # Example: "TRIGGER:P0DT9H0M0S" means 9 hours before
            # "TRIGGER:PT0S" means at the time
            if diff.total_seconds() <= 0:
                # If reminder is in the past or now, set to "at time"
                return "TRIGGER:PT0S"
            
            days = diff.days
            hours = diff.seconds // 3600
            minutes = (diff.seconds % 3600) // 60
            seconds = diff.seconds % 60
            
            return f"TRIGGER:P{days}DT{hours}H{minutes}M{seconds}S"
        except Exception as e:
            self.logger.warning(f"Failed to convert reminder time {reminder_time}: {e}")
            # Default to "at time"
            return "TRIGGER:PT0S"
    
    async def get_projects(self) -> List[Dict[str, Any]]:
        """
        Get list of projects/lists
        
        Returns:
            List of projects
        """
        if not self.access_token:
            await self.authenticate()
        
        response = await self.get(
            endpoint=f"/open/{TICKTICK_API_VERSION}/project",
            headers=self._get_headers(),
        )
        
        if isinstance(response, list):
            return response
        elif "projects" in response:
            return response["projects"]
        else:
            return []
    
    async def create_project(
        self,
        name: str,
        color: Optional[str] = None,
        view_mode: Optional[str] = None,
        kind: Optional[str] = None,
        sort_order: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Create a new project
        
        Args:
            name: Project name (required)
            color: Project color (e.g., "#F18181")
            view_mode: View mode ("list", "kanban", "timeline")
            kind: Project kind ("TASK", "NOTE")
            sort_order: Sort order
            
        Returns:
            Created project data
        """
        if not self.access_token:
            await self.authenticate()
        
        if not name:
            raise ValueError("Project name is required")
        
        project_data = {
            "name": name,
        }
        
        # Only add optional parameters if they are provided
        if color:
            project_data["color"] = color
        
        if view_mode:
            project_data["viewMode"] = view_mode
        
        if kind:
            project_data["kind"] = kind
        
        if sort_order is not None:
            project_data["sortOrder"] = sort_order
        
        return await self.post(
            endpoint=f"/open/{TICKTICK_API_VERSION}/project",
            headers=self._get_headers(),
            json_data=project_data,
        )

