"""
Task management service
"""

import re
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta

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
from src.api.ticktick_client import TickTickClient
from src.models.task import Task, TaskCreate, TaskUpdate
from src.models.command import ParsedCommand
from src.utils.logger import logger
from src.utils.date_parser import parse_date
from src.services.task_cache import TaskCacheService
from src.services.project_cache_service import ProjectCacheService
from src.services.task_search_service import TaskSearchService
from src.utils.formatters import (
    format_task_created,
    format_task_updated,
    format_task_deleted,
    format_task_completed,
)


class TaskManager:
    """Service for managing tasks"""
    
    def __init__(self, ticktick_client: TickTickClient):
        """
        Initialize task manager
        
        Args:
            ticktick_client: TickTick API client
        """
        self.client = ticktick_client
        self.cache = TaskCacheService()
        self.project_cache = ProjectCacheService(ticktick_client)
        self.task_search = TaskSearchService(ticktick_client, self.cache, self.project_cache)
        self.logger = logger
        
        # Import TICKTICK_API_VERSION for endpoint construction
        from src.config.constants import TICKTICK_API_VERSION
        self.api_version = TICKTICK_API_VERSION
    
    async def _resolve_project_id(self, project_identifier: Optional[str]) -> Optional[str]:
        """
        Resolve project identifier (name or ID) to project ID
        
        Args:
            project_identifier: Project name or ID
            
        Returns:
            Project ID or None if not found
        """
        if not project_identifier:
            self.logger.debug("No project identifier provided")
            return None
        
        self.logger.debug(f"Resolving project identifier: '{project_identifier}'")
        
        # Check if GPT returned a placeholder instead of real ID
        # Common placeholders: "ID_ПРОЕКТА_РАБОТА_ИЗ_КОНТЕКСТА", "ID_ПРОЕКТА_ЛИЧНОЕ_ИЗ_КОНТЕКСТА", etc.
        placeholder_patterns = [
            r"ID_ПРОЕКТА_(\w+)_ИЗ_КОНТЕКСТА",
            r"ID_ПРОЕКТА_(\w+)",
            r"ID_(\w+)_ИЗ_КОНТЕКСТА",
        ]
        
        for pattern in placeholder_patterns:
            match = re.search(pattern, project_identifier, re.IGNORECASE)
            if match:
                # Extract project name from placeholder
                extracted_name = match.group(1)
                self.logger.warning(
                    f"⚠ GPT returned placeholder '{project_identifier}'. "
                    f"Extracted project name: '{extracted_name}'. "
                    f"Attempting to resolve by name..."
                )
                # Try to resolve by extracted name
                project_identifier = extracted_name
                break
        
        # Check if it looks like an ID (starts with "inbox" or is UUID-like)
        # If it's already an ID, return as is
        if project_identifier.startswith("inbox") or len(project_identifier) > 20:
            self.logger.debug(f"Project identifier '{project_identifier}' looks like an ID, returning as is")
            return project_identifier
        
        # Otherwise, it's likely a project name - search for it
        try:
            projects = await self.client.get_projects()
            self.logger.debug(f"Retrieved {len(projects)} projects for search")
            
            project_identifier_lower = project_identifier.lower().strip()
            
            # First, try exact match (case-insensitive, emoji-insensitive)
            for project in projects:
                project_name = project.get('name', '').strip()
                project_id = project.get('id')
                
                if not project_name or not project_id:
                    continue
                
                # Clean project name (remove emojis) for matching
                cleaned_project_name = _clean_project_name(project_name).lower()
                
                if cleaned_project_name == project_identifier_lower:
                    self.logger.info(f"✓ Exact match found: project '{project_name}' (ID: {project_id})")
                    return project_id
            
            # If exact match not found, try partial match (contains)
            self.logger.debug(f"Exact match not found, trying partial match for '{project_identifier}'")
            matches = []
            
            for project in projects:
                project_name = project.get('name', '').strip()
                project_id = project.get('id')
                
                if not project_name or not project_id:
                    continue
                
                # Clean project name (remove emojis) for matching
                cleaned_project_name = _clean_project_name(project_name).lower()
                project_name_lower = cleaned_project_name
                
                # Check if cleaned project name contains identifier or vice versa
                if (project_identifier_lower in project_name_lower or 
                    project_name_lower in project_identifier_lower):
                    matches.append((project_name, project_id))
            
            if matches:
                # If multiple matches, prefer the one with shorter name (more specific)
                matches.sort(key=lambda x: len(x[0]))
                best_match = matches[0]
                self.logger.info(f"✓ Partial match found: project '{best_match[0]}' (ID: {best_match[1]}) for '{project_identifier}'")
                if len(matches) > 1:
                    self.logger.warning(f"Multiple matches found: {[m[0] for m in matches]}, using '{best_match[0]}'")
                return best_match[1]
            
            # If not found, log available projects for debugging
            available_projects = [p.get('name', '') for p in projects if p.get('name')]
            self.logger.warning(
                f"Project '{project_identifier}' not found. "
                f"Available projects: {', '.join(available_projects[:10])}"
                f"{'...' if len(available_projects) > 10 else ''}"
            )
            return None
            
        except Exception as e:
            self.logger.error(f"Failed to resolve project '{project_identifier}': {e}", exc_info=True)
            return None
    
    async def create_task(self, command: ParsedCommand) -> str:
        """
        Create a new task
        
        Args:
            command: Parsed command with task details
            
        Returns:
            Success message
        """
        try:
            if not command.title:
                raise ValueError("Название задачи не указано")
            
            self.logger.debug(f"Creating task: title='{command.title}', project_id from command='{command.project_id}'")
            
            # Resolve project_id if project name is provided
            original_project_id = command.project_id
            project_id = await self._resolve_project_id(command.project_id)
            
            # Log project resolution result
            if original_project_id:
                if project_id:
                    self.logger.info(f"✓ Project resolved: '{original_project_id}' -> '{project_id}'")
                else:
                    self.logger.warning(
                        f"⚠ Project '{original_project_id}' not found. "
                        f"Task will be created in default inbox. "
                        f"Check if project name is correct or project exists in TickTick."
                    )
            else:
                self.logger.debug("No project specified, task will be created in default inbox")
            
            # Parse due date if provided
            due_date = command.due_date
            if due_date:
                parsed_date = parse_date(due_date)
                if parsed_date:
                    due_date = parsed_date
            
            self.logger.debug(f"Creating task with project_id='{project_id}', due_date='{due_date}'")
            
            task_data = await self.client.create_task(
                title=command.title,
                project_id=project_id,
                due_date=due_date,
                priority=command.priority or 0,
                tags=command.tags or [],
                notes=command.notes,
            )
            
            task_id = task_data.get('id')
            actual_project_id = task_data.get('projectId')
            
            self.logger.info(
                f"Task created: id='{task_id}', "
                f"title='{command.title}', "
                f"project_id='{actual_project_id}'"
            )
            
            # Validate that task was created in expected project
            if original_project_id and project_id and actual_project_id != project_id:
                self.logger.warning(
                    f"⚠ Project mismatch: expected '{project_id}', but task created in '{actual_project_id}'"
                )
            
            # Save to cache for future lookups
            if task_id:
                # Use resolved project_id (or fallback to task_data)
                resolved_project_id = project_id or actual_project_id
                self.cache.save_task(
                    task_id=task_id,
                    title=command.title,
                    project_id=resolved_project_id,
                )
                self.logger.debug(f"Task saved to cache: id='{task_id}', project_id='{resolved_project_id}'")
            
            return format_task_created(task_data)
            
        except Exception as e:
            self.logger.error(f"Error creating task: {e}", exc_info=True)
            raise
    
    async def update_task(self, command: ParsedCommand) -> str:
        """
        Update existing task
        
        Args:
            command: Parsed command with update details
            
        Returns:
            Success message
        """
        try:
            if not command.task_id:
                if not command.title:
                    raise ValueError("Не указано название задачи или ID для обновления")
                
                # Use TaskSearchService to find task
                task = await self.task_search.find_task_by_title(
                    title=command.title,
                    project_id=command.project_id,
                )
                
                if task:
                    command.task_id = task.get("id")
                    self.logger.debug(f"Found task ID: {command.task_id}")
                else:
                    raise ValueError(
                        f"Задача '{command.title}' не найдена. "
                        f"Попробуйте создать новую задачу или укажите ID задачи."
                    )
            
            # Get current task data from cache to merge tags and notes
            original_task_data = self.cache.get_task_data(command.task_id)
            
            # Build update data - merge with existing data when needed
            update_data = {}
            
            # Handle task move (targetProjectId) - if specified, change project
            if command.target_project_id:
                update_data["projectId"] = command.target_project_id
            elif command.project_id:
                update_data["projectId"] = command.project_id
            
            # Handle due date
            if command.due_date:
                parsed_date = parse_date(command.due_date)
                if parsed_date:
                    update_data["dueDate"] = parsed_date
                else:
                    update_data["dueDate"] = command.due_date
            
            # Handle priority
            if command.priority is not None:
                update_data["priority"] = command.priority
            
            # Handle tags - merge with existing tags (like TagManager does)
            if command.tags:
                if original_task_data:
                    existing_tags = original_task_data.get('tags', [])
                    if not isinstance(existing_tags, list):
                        existing_tags = []
                    # Merge tags and remove duplicates
                    merged_tags = list(set(existing_tags + command.tags))
                    update_data["tags"] = merged_tags
                else:
                    # If no cache data, just use new tags
                    update_data["tags"] = command.tags
            
            # Handle notes - merge with existing notes (like NoteManager does)
            if command.notes:
                if original_task_data:
                    existing_notes = original_task_data.get('notes', '')
                    if existing_notes:
                        combined_notes = f"{existing_notes}\n\n{command.notes}"
                    else:
                        combined_notes = command.notes
                    update_data["content"] = combined_notes
                else:
                    # If no cache data, just use new notes
                    update_data["content"] = command.notes
            
            # Handle title update - if title is provided and different from search title
            # Note: GPT should parse new title separately, but for now we check if title differs
            if command.title and original_task_data:
                original_title = original_task_data.get('title', '')
                if command.title.lower() != original_title.lower():
                    # Title seems to be updated
                    update_data["title"] = command.title
            
            # If no fields to update, return error
            if not update_data:
                raise ValueError("Не указаны параметры для обновления")
            
            # Update task using correct API endpoint (POST /open/v1/task/{taskId})
            task_data = await self.client.update_task(
                task_id=command.task_id,
                **update_data
            )
            self.logger.info(f"Task updated: {command.task_id}")
            
            # Update cache if project was changed
            if command.target_project_id:
                task_info = self.cache.get_task_data(command.task_id)
                if task_info:
                    self.cache.save_task(
                        task_id=command.task_id,
                        title=task_info.get('title', '') or command.title or '',
                        project_id=command.target_project_id,
                        status=task_info.get('status', 'active'),
                    )
            
            # Update cache with new tags and notes if they were added
            if command.tags or command.notes:
                task_info = self.cache.get_task_data(command.task_id)
                if task_info:
                    # Update cache with merged tags and notes
                    if command.tags:
                        task_info['tags'] = update_data.get('tags', [])
                    if command.notes:
                        task_info['notes'] = update_data.get('content', '')
                    self.cache._cache[command.task_id] = task_info
                    self.cache._save_cache()
            
            # Pass update_data to formatter to show only changed fields
            task_title = self.cache.get_task_data(command.task_id)
            title = task_title.get('title', '') if task_title else command.title or 'задача'
            return format_task_updated({**update_data, 'title': title})
            
        except ValueError:
            # Re-raise ValueError as-is (it's already user-friendly)
            raise
        except Exception as e:
            self.logger.error(f"Error updating task: {e}", exc_info=True)
            raise
    
    
    async def delete_task(self, command: ParsedCommand) -> str:
        """
        Delete task
        
        Args:
            command: Parsed command with task ID or title
            
        Returns:
            Success message
        """
        try:
            if not command.task_id:
                if not command.title:
                    raise ValueError("Не указано название задачи или ID для удаления")
                
                # Use TaskSearchService to find task
                task = await self.task_search.find_task_by_title(
                    title=command.title,
                    project_id=command.project_id,
                )
                
                if task:
                    command.task_id = task.get("id")
                    title = task.get("title", command.title)
                    self.logger.debug(f"Found task ID: {command.task_id}")
                else:
                    raise ValueError(
                        f"Задача '{command.title}' не найдена. "
                        f"Попробуйте создать новую задачу или укажите ID задачи."
                    )
            else:
                # Get task title from cache
                task_data = self.cache.get_task_data(command.task_id)
                title = task_data.get("title", "Задача") if task_data else "Задача"
            
            # Get project_id for delete (required by API)
            project_id = command.project_id
            if not project_id:
                task_data = self.cache.get_task_data(command.task_id)
                if task_data:
                    project_id = task_data.get('project_id')
            
            # Delete task using correct API endpoint (DELETE /open/v1/project/{projectId}/task/{taskId})
            await self.client.delete_task(command.task_id, project_id=project_id)
            # Remove from cache
            self.cache.delete_task(command.task_id)
            self.logger.info(f"Task deleted: {command.task_id}")
            return format_task_deleted(title)
            
        except ValueError:
            # Re-raise ValueError as-is (it's already user-friendly)
            raise
        except Exception as e:
            self.logger.error(f"Error deleting task: {e}", exc_info=True)
            raise
    
    async def complete_task(self, command: ParsedCommand) -> str:
        """
        Complete task (mark as done)
        
        Args:
            command: Parsed command with task ID or title
            
        Returns:
            Success message
        """
        try:
            if not command.task_id:
                if not command.title:
                    raise ValueError("Не указано название задачи или ID для завершения")
                
                # Use TaskSearchService to find task
                task = await self.task_search.find_task_by_title(
                    title=command.title,
                    project_id=command.project_id,
                )
                
                if task:
                    command.task_id = task.get("id")
                    title = task.get("title", command.title)
                    self.logger.debug(f"Found task ID: {command.task_id}")
                else:
                    raise ValueError(
                        f"Задача '{command.title}' не найдена. "
                        f"Попробуйте создать новую задачу или укажите ID задачи."
                    )
            else:
                # Get task title from cache
                task_data = self.cache.get_task_data(command.task_id)
                title = task_data.get("title", "Задача") if task_data else "Задача"
            
            # Check if task is already completed
            task_data = self.cache.get_task_data(command.task_id)
            if task_data and task_data.get('status') == 'completed':
                return f"Задача '{title}' уже выполнена"
            
            # Get project_id for complete (required by API)
            project_id = command.project_id
            if not project_id:
                task_data = self.cache.get_task_data(command.task_id)
                if task_data:
                    project_id = task_data.get('project_id')
            
            if not project_id:
                raise ValueError(
                    f"Не найден project_id для задачи {command.task_id}. "
                    f"Попробуйте указать список задачи."
                )
            
            # Complete task using correct API endpoint (POST /open/v1/project/{projectId}/task/{taskId}/complete)
            await self.client.complete_task(command.task_id, project_id=project_id)
            # Cache is updated automatically in TickTickClient.complete_task
            self.logger.info(f"Task completed: {command.task_id}")
            return format_task_completed(title)
            
        except ValueError:
            # Re-raise ValueError as-is (it's already user-friendly)
            raise
        except Exception as e:
            self.logger.error(f"Error completing task: {e}", exc_info=True)
            raise
    
    async def move_task(self, command: ParsedCommand) -> str:
        """
        Move task to different project/list
        
        Args:
            command: Parsed command with task ID and target project
            
        Returns:
            Success message
        """
        try:
            if not command.task_id:
                # Try to find task by title
                if not command.title:
                    raise ValueError("Задача не указана")
                
                # Use TaskSearchService to find task
                task = await self.task_search.find_task_by_title(
                    title=command.title,
                    project_id=command.project_id,
                )
                
                if task:
                    command.task_id = task.get("id")
                    self.logger.debug(f"Found task ID: {command.task_id}")
                else:
                    raise ValueError(
                        f"Задача '{command.title}' не найдена. "
                        f"Создайте задачу через бота или используйте task_id."
                    )
            
            if not command.target_project_id:
                raise ValueError("Целевой список не указан")
            
            self.logger.debug(
                f"Moving task: task_id='{command.task_id}', "
                f"target_project_id from command='{command.target_project_id}'"
            )
            
            # Resolve target project_id (name or ID)
            original_target_project_id = command.target_project_id
            target_project_id = await self._resolve_project_id(command.target_project_id)
            
            # Log project resolution result
            if target_project_id:
                self.logger.info(f"✓ Target project resolved: '{original_target_project_id}' -> '{target_project_id}'")
            else:
                self.logger.error(
                    f"✗ Failed to resolve target project: '{original_target_project_id}'. "
                    f"This might be a placeholder returned by GPT instead of real ID."
                )
                raise ValueError(f"Список '{original_target_project_id}' не найден. Проверьте правильность названия или создайте список сначала.")
            
            # Verify target project exists
            try:
                projects = await self.client.get_projects()
                target_project = next((p for p in projects if p.get('id') == target_project_id), None)
                if not target_project:
                    self.logger.error(
                        f"✗ Target project ID '{target_project_id}' not found in projects list. "
                        f"Available projects: {[p.get('name', '') for p in projects[:5]]}"
                    )
                    raise ValueError(f"Целевой список '{target_project_id}' не найден. Проверьте правильность ID или создайте список сначала.")
                self.logger.debug(f"Target project verified: {target_project.get('name', target_project_id)}")
            except ValueError:
                # Re-raise ValueError as-is
                raise
            except Exception as verify_error:
                self.logger.error(f"Error verifying target project: {verify_error}", exc_info=True)
                raise ValueError(f"Не удалось проверить существование целевого списка: {verify_error}")
            
            # Get current task data
            current_task_info = self.cache.get_task_data(command.task_id)
            if not current_task_info:
                raise ValueError(f"Задача {command.task_id} не найдена в кэше")
            
            current_project_id = current_task_info.get('project_id')
            if not current_project_id:
                raise ValueError(f"Не найден project_id для задачи {command.task_id}")
            
            # Try to move via update_task first (direct API call)
            try:
                task_data = await self.client.update_task(
                    task_id=command.task_id,
                    project_id=target_project_id,
                )
                self.logger.info(f"Task moved via update_task: {command.task_id} -> {target_project_id}")
                
                # Wait a bit and verify move
                import asyncio
                await asyncio.sleep(2)
                
                # Verify move by checking target project
                try:
                    target_tasks = await self.client.get_tasks(project_id=target_project_id)
                    task_moved = any(t.get('id') == command.task_id for t in target_tasks)
                    
                    if task_moved:
                        # Update cache with new project_id
                        project_name = target_project.get('name', target_project_id) if target_project else target_project_id
                        self.cache.save_task(
                            task_id=command.task_id,
                            title=current_task_info.get('title', ''),
                            project_id=target_project_id,
                            status=current_task_info.get('status', 'active'),
                        )
                        return f"✓ Задача перемещена в список {project_name}"
                    else:
                        # Move didn't work, use fallback
                        self.logger.warning(f"update_task didn't move task, using fallback method")
                        raise ValueError("Move via update_task failed")
                except Exception as verify_error:
                    self.logger.warning(f"Could not verify move: {verify_error}, using fallback")
                    raise ValueError("Move verification failed")
                    
            except Exception as update_error:
                # Fallback: create new task in target project and delete old one
                self.logger.info(f"Using fallback move method: create+delete")
                
                # Get full task data
                try:
                    full_task = await self.client.get(
                        endpoint=f"/open/{self.api_version}/project/{current_project_id}/task/{command.task_id}",
                        headers=self.client._get_headers(),
                    )
                except Exception as get_error:
                    # If we can't get full task, use cached data
                    self.logger.warning(f"Could not get full task data: {get_error}, using cached data")
                    full_task = {
                        'title': current_task_info.get('title', ''),
                        'priority': current_task_info.get('priority', 0),
                        'tags': current_task_info.get('tags', []),
                        'content': current_task_info.get('notes', ''),
                    }
                
                # Create new task in target project
                new_task_data = {
                    'title': full_task.get('title', current_task_info.get('title', '')),
                    'project_id': target_project_id,
                }
                
                # Copy optional fields
                for field in ['priority', 'tags', 'notes', 'due_date', 'repeat_flag', 'reminders']:
                    if field in full_task and full_task[field] is not None:
                        new_task_data[field] = full_task[field]
                    elif field == 'notes' and 'content' in full_task:
                        new_task_data['notes'] = full_task.get('content')
                
                new_task = await self.client.create_task(**new_task_data)
                new_task_id = new_task.get('id')
                
                # Delete old task
                try:
                    await self.client.delete_task(command.task_id, current_project_id)
                except Exception as delete_error:
                    self.logger.warning(f"Could not delete old task: {delete_error}")
                    # Continue anyway - task was created in new project
                
                # Update cache: remove old, add new with mapping
                self.cache._cache.pop(command.task_id, None)
                self.cache.save_task(
                    task_id=new_task_id,
                    title=new_task_data.get('title', ''),
                    project_id=target_project_id,
                    status='active',
                    original_task_id=command.task_id,  # Save mapping for reference
                )
                
                project_name = target_project.get('name', target_project_id) if target_project else target_project_id
                self.logger.info(f"Task moved via create+delete: {command.task_id} -> {new_task_id} (in {target_project_id})")
                return f"✓ Задача перемещена в список {project_name} (новая задача: {new_task_id})"
            
        except ValueError:
            raise
        except Exception as e:
            self.logger.error(f"Error moving task: {e}", exc_info=True)
            raise
    

