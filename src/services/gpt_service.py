"""
GPT service for parsing commands
"""

import json
import re
from typing import Dict, Any, Optional
from src.api.openai_client import OpenAIClient
from src.api.ticktick_client import TickTickClient
from src.services.prompt_manager import PromptManager
from src.services.data_fetcher import DataFetcher
from src.models.command import ParsedCommand
from src.utils.logger import logger


class GPTService:
    """Service for parsing commands using GPT"""
    
    def __init__(self, ticktick_client: Optional[TickTickClient] = None):
        """
        Initialize GPT service
        
        Args:
            ticktick_client: TickTick client for getting projects context (optional)
        """
        self.openai_client = OpenAIClient()
        self.prompt_manager = PromptManager()
        self.ticktick_client = ticktick_client
        self.logger = logger
    
    async def parse_command(self, command: str) -> ParsedCommand:
        """
        Parse user command using multi-stage GPT process
        
        Stage 1: GPT determines what data is needed
        Stage 2: System fetches data from cache/API
        Stage 3: GPT formats JSON with real data and examples
        
        Args:
            command: User command text
            
        Returns:
            ParsedCommand object
            
        Raises:
            ValueError: If parsing fails
        """
        try:
            self.logger.info(f"[Multi-stage] Starting command parsing: {command}")
            
            # Log client status
            if self.ticktick_client:
                self.logger.debug(f"[Multi-stage] TickTick client available: {type(self.ticktick_client).__name__}")
                self.logger.debug(f"[Multi-stage] TickTick client has access_token: {hasattr(self.ticktick_client, 'access_token') and bool(self.ticktick_client.access_token)}")
            else:
                self.logger.error("[Multi-stage] TickTick client is None!")
                raise ValueError("TickTick client not available for data fetching")
            
            # Stage 1: Determine data requirements
            self.logger.info("[Stage 1] Determining data requirements...")
            requirements = await self.determine_data_requirements(command)
            action_type = requirements.get("action_type", "create_task")
            self.logger.info(f"[Stage 1] Action type determined: {action_type}")
            self.logger.debug(f"[Stage 1] Requirements: {requirements}")
            
            self.logger.info(f"[Stage 2] Fetching data for requirements...")
            
            # Stage 2: Fetch data
            if not self.ticktick_client:
                self.logger.error("[Stage 2] TickTick client is None after Stage 1!")
                raise ValueError("TickTick client not available for data fetching")
            
            # Ensure client is authenticated before fetching data
            try:
                if not hasattr(self.ticktick_client, 'access_token') or not self.ticktick_client.access_token:
                    self.logger.info("[Stage 2] Authenticating TickTick client...")
                    auth_result = await self.ticktick_client.authenticate()
                    self.logger.info(f"[Stage 2] Authentication result: {auth_result}")
                else:
                    self.logger.debug("[Stage 2] TickTick client already authenticated")
            except Exception as e:
                self.logger.error(f"[Stage 2] Authentication error: {e}", exc_info=True)
                raise ValueError(f"Ошибка аутентификации TickTick: {str(e)}")
            
            data_fetcher = DataFetcher(self.ticktick_client)
            self.logger.debug(f"[Stage 2] DataFetcher created, fetching data...")
            fetched_data = await data_fetcher.fetch_data_requirements(requirements)
            self.logger.debug(f"[Stage 2] Data fetched: {len(fetched_data.get('tasks', {}))} tasks, {len(fetched_data.get('projects', {}))} projects")
            
            # If current_task_data is needed but not yet fetched, fetch it using task_id from tasks
            required_data = requirements.get("required_data", {})
            if required_data.get("current_task_data") or self._needs_current_data(action_type):
                # Find task_ids from fetched tasks
                for title, task in fetched_data.get("tasks", {}).items():
                    if task and task.get("id"):
                        task_id = task.get("id")
                        # Fetch current task data if not already fetched
                        if task_id not in fetched_data.get("current_task_data", {}):
                            if "current_task_data" not in fetched_data:
                                fetched_data["current_task_data"] = {}
                            task_data = await data_fetcher.fetch_task_data(task_id)
                            fetched_data["current_task_data"][task_id] = task_data
                            self.logger.debug(f"[Stage 2] Fetched current data for task {task_id}")
            
            # Check for missing data
            missing_error = self._check_missing_data(requirements, fetched_data)
            if missing_error:
                self.logger.warning(f"[Stage 2] Missing data: {missing_error}")
                raise ValueError(missing_error)
            
            self.logger.info(f"[Stage 2] Data fetched successfully")
            
            # Stage 3: Parse command with data
            parsed_command = await self.parse_command_with_data(
                command, fetched_data, action_type
            )
            
            self.logger.info(f"[Multi-stage] Command parsing completed successfully")
            
            return parsed_command
            
        except ValueError:
            # Re-raise ValueError as-is (these are user-friendly error messages)
            raise
        except Exception as e:
            self.logger.error(f"[Multi-stage] Error parsing command: {e}", exc_info=True)
            raise ValueError(f"Не удалось обработать команду: {str(e)}")
    
    def _needs_current_data(self, action_type: str) -> bool:
        """
        Check if action type needs current task data (for merge/append operations)
        
        Args:
            action_type: Action type
            
        Returns:
            True if current data is needed
        """
        actions_needing_current_data = [
            "add_tags",  # Need to merge with existing tags
            "add_note",  # Need to append to existing notes
            "update_task",  # May need current data for merge operations
        ]
        return action_type in actions_needing_current_data
    
    async def _get_context_for_parsing(self) -> Dict[str, Any]:
        """
        Get context information (projects only) for GPT parsing
        
        Returns:
            Dictionary with context information (only projects, no tasks)
        """
        context = {
            "projects": [],
        }
        
        if not self.ticktick_client:
            self.logger.warning("TickTick client not available, cannot get projects context")
            return context
        
        try:
            # Get projects list only
            projects = await self.ticktick_client.get_projects()
            
            # Helper function to remove emojis and normalize name
            import re
            def clean_name(name: str) -> str:
                """Remove emojis and extra spaces from project name"""
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
            
            context["projects"] = []
            for p in projects:
                original_name = p.get("name", "")
                cleaned_name = clean_name(original_name)
                context["projects"].append({
                    "id": p.get("id", ""),
                    "name": original_name,  # Keep original for display
                    "name_clean": cleaned_name,  # Clean name for matching
                })
            
            self.logger.debug(f"Retrieved {len(context['projects'])} projects for context")
            
            # Log project names for debugging (first 10)
            if context["projects"]:
                project_names = [p["name"] for p in context["projects"][:10]]
                self.logger.debug(f"Projects available: {', '.join(project_names)}{'...' if len(context['projects']) > 10 else ''}")
            
        except Exception as e:
            self.logger.error(f"Failed to get context for parsing: {e}", exc_info=True)
            # Continue without context - better than failing completely
        
        return context
    
    def _get_project_name_by_id(self, projects: list, project_id: str) -> str:
        """Get project name by ID"""
        for project in projects:
            if project.get("id") == project_id:
                return project.get("name", "")
        return ""
    
    async def determine_urgency(
        self,
        tasks: list,
        goals: Optional[list] = None,
    ) -> Dict[str, str]:
        """
        Determine urgency for tasks using GPT
        
        Args:
            tasks: List of tasks
            goals: List of weekly goals (optional)
            
        Returns:
            Dictionary mapping task IDs to urgency levels (urgent, medium, low)
        """
        try:
            prompt = f"""Проанализируй следующие задачи и определи уровень срочности для каждой на основе целей недели.
            
Цели недели: {goals or "Не указаны"}
            
Задачи:
{self._format_tasks_for_gpt(tasks)}
            
Верни JSON с полями: taskId -> urgency (urgent, medium, low)"""
            
            response = await self.openai_client.chat_completion([
                {"role": "system", "content": "Ты - эксперт по управлению временем и приоритизации задач."},
                {"role": "user", "content": prompt},
            ])
            
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                urgency_map = json.loads(json_match.group(0))
            else:
                urgency_map = json.loads(response)
            
            return urgency_map
            
        except Exception as e:
            self.logger.error(f"Error determining urgency: {e}", exc_info=True)
            # Return default urgency
            return {task.get("id", ""): "medium" for task in tasks}
    
    def _format_tasks_for_gpt(self, tasks: list) -> str:
        """Format tasks for GPT prompt"""
        formatted = []
        for task in tasks:
            formatted.append(
                f"- {task.get('title', '')} (ID: {task.get('id', '')}, "
                f"Due: {task.get('dueDate', 'Не указана')})"
            )
        return "\n".join(formatted)
    
    async def determine_data_requirements(self, command: str) -> Dict[str, Any]:
        """
        Stage 1: Determine what data is needed for command execution
        
        Args:
            command: User command text
            
        Returns:
            Dictionary with action_type and required_data
            
        Raises:
            ValueError: If GPT cannot determine requirements
        """
        try:
            self.logger.info(f"[Stage 1] Determining data requirements for command: {command}")
            
            system_prompt = self.prompt_manager.get_stage1_prompt()
            
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": command},
            ]
            
            response = await self.openai_client.chat_completion(messages=messages)
            
            # Parse JSON from response
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
            else:
                json_str = response.strip()
            
            # Clean up JSON string
            json_str = json_str.strip()
            if json_str.startswith('```json'):
                json_str = json_str[7:]
            if json_str.startswith('```'):
                json_str = json_str[3:]
            if json_str.endswith('```'):
                json_str = json_str[:-3]
            json_str = json_str.strip()
            
            try:
                requirements = json.loads(json_str)
                self.logger.info(f"[Stage 1] Requirements determined: {requirements}")
                return requirements
            except json.JSONDecodeError as e:
                self.logger.error(f"[Stage 1] Failed to parse JSON: {json_str}")
                raise ValueError(f"Не удалось определить требования к данным: {e}")
                
        except Exception as e:
            self.logger.error(f"[Stage 1] Error determining data requirements: {e}", exc_info=True)
            raise ValueError(f"Не удалось обработать команду: {str(e)}")
    
    async def parse_command_with_data(
        self, 
        command: str, 
        fetched_data: Dict[str, Any], 
        action_type: str
    ) -> ParsedCommand:
        """
        Stage 3: Parse command with fetched data and examples
        
        Args:
            command: Original user command
            fetched_data: Data fetched in stage 2
            action_type: Type of action determined in stage 1
            
        Returns:
            ParsedCommand object
            
        Raises:
            ValueError: If parsing fails
        """
        try:
            self.logger.info(f"[Stage 3] Parsing command with data for action: {action_type}")
            
            # Format fetched data for GPT
            formatted_data = self._format_fetched_data_for_gpt(fetched_data)
            
            # Prepare example data for prompt
            example_data = self._prepare_example_data(fetched_data, action_type)
            
            # Get stage 3 prompt with examples
            system_prompt = self.prompt_manager.get_stage3_prompt(action_type, example_data)
            
            # Build user message with command and data
            user_message = f"""ИСХОДНАЯ КОМАНДА ПОЛЬЗОВАТЕЛЯ:
{command}

ПОЛУЧЕННЫЕ ДАННЫЕ:
{formatted_data}

Сформируй JSON для выполнения команды, используя РЕАЛЬНЫЕ ID из полученных данных."""
            
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ]
            
            response = await self.openai_client.chat_completion(messages=messages)
            
            # Parse JSON from response
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
            else:
                json_str = response.strip()
            
            # Clean up JSON string
            json_str = json_str.strip()
            if json_str.startswith('```json'):
                json_str = json_str[7:]
            if json_str.startswith('```'):
                json_str = json_str[3:]
            if json_str.endswith('```'):
                json_str = json_str[:-3]
            json_str = json_str.strip()
            
            try:
                parsed_dict = json.loads(json_str)
                
                # Check for errors
                if "error" in parsed_dict:
                    error_msg = parsed_dict["error"]
                    self.logger.warning(f"[Stage 3] GPT returned error: {error_msg}")
                    raise ValueError(error_msg)
                
                # Create ParsedCommand object
                parsed_command = ParsedCommand(**parsed_dict)
                
                self.logger.info(
                    f"[Stage 3] Command parsed: action='{parsed_command.action}', "
                    f"task_id='{parsed_command.task_id}', project_id='{parsed_command.project_id}'"
                )
                
                return parsed_command
                
            except json.JSONDecodeError as e:
                self.logger.error(f"[Stage 3] Failed to parse JSON: {json_str}")
                raise ValueError(f"Не удалось распарсить ответ GPT: {e}")
                
        except Exception as e:
            self.logger.error(f"[Stage 3] Error parsing command with data: {e}", exc_info=True)
            raise ValueError(f"Не удалось обработать команду: {str(e)}")
    
    def _check_missing_data(
        self, 
        requirements: Dict[str, Any], 
        fetched_data: Dict[str, Any]
    ) -> Optional[str]:
        """
        Check if any required data is missing
        
        Args:
            requirements: Requirements from stage 1
            fetched_data: Fetched data from stage 2
            
        Returns:
            Error message if data is missing, None otherwise
        """
        required_data = requirements.get("required_data", {})
        missing = []
        
        # Check tasks by title
        task_titles = required_data.get("task_by_title", [])
        for title in task_titles:
            if title not in fetched_data.get("tasks", {}) or fetched_data["tasks"][title] is None:
                missing.append(f"Задача '{title}'")
        
        # Check projects by name
        project_names = required_data.get("project_by_name", [])
        for name in project_names:
            if name not in fetched_data.get("projects", {}) or fetched_data["projects"][name] is None:
                missing.append(f"Проект '{name}'")
        
        # Check task data
        task_ids = required_data.get("task_data", [])
        for task_id in task_ids:
            if task_id not in fetched_data.get("task_data", {}) or fetched_data["task_data"][task_id] is None:
                missing.append(f"Данные задачи '{task_id}'")
        
        if missing:
            return f"Не найдено: {', '.join(missing)}. Попробуйте создать новую задачу или укажите правильное название."
        
        return None
    
    def _format_fetched_data_for_gpt(self, fetched_data: Dict[str, Any]) -> str:
        """
        Format fetched data for GPT prompt
        
        Args:
            fetched_data: Fetched data dictionary
            
        Returns:
            Formatted string for GPT
        """
        lines = []
        
        # Format tasks
        if fetched_data.get("tasks"):
            lines.append("НАЙДЕННЫЕ ЗАДАЧИ:")
            for title, task in fetched_data["tasks"].items():
                if task:
                    lines.append(f"  - '{title}': {{id: '{task.get('id')}', projectId: '{task.get('projectId')}', title: '{task.get('title')}'}}")
                else:
                    lines.append(f"  - '{title}': НЕ НАЙДЕНА")
            lines.append("")
        
        # Format projects
        if fetched_data.get("projects"):
            lines.append("НАЙДЕННЫЕ ПРОЕКТЫ:")
            for name, project in fetched_data["projects"].items():
                if project:
                    lines.append(f"  - '{name}': {{id: '{project.get('id')}', name: '{project.get('name')}'}}")
                else:
                    lines.append(f"  - '{name}': НЕ НАЙДЕН")
            lines.append("")
        
        # Format task data
        if fetched_data.get("task_data"):
            lines.append("ДАННЫЕ ЗАДАЧ:")
            for task_id, task_data in fetched_data["task_data"].items():
                if task_data:
                    lines.append(f"  - '{task_id}': {json.dumps(task_data, ensure_ascii=False)}")
                else:
                    lines.append(f"  - '{task_id}': НЕ НАЙДЕНЫ")
            lines.append("")
        
        # Format current task data
        if fetched_data.get("current_task_data"):
            lines.append("ТЕКУЩИЕ ДАННЫЕ ЗАДАЧ (для merge/append операций):")
            for task_id, task_data in fetched_data["current_task_data"].items():
                if task_data:
                    lines.append(f"  - '{task_id}': {json.dumps(task_data, ensure_ascii=False)}")
                else:
                    lines.append(f"  - '{task_id}': НЕ НАЙДЕНЫ")
            lines.append("")
        
        return "\n".join(lines)
    
    def _prepare_example_data(
        self, 
        fetched_data: Dict[str, Any], 
        action_type: str
    ) -> Dict[str, Any]:
        """
        Prepare example data structure for prompt
        
        Args:
            fetched_data: Fetched data
            action_type: Action type
            
        Returns:
            Example data dictionary
        """
        example = {}
        
        # Try to get first task
        if fetched_data.get("tasks"):
            first_task_title = list(fetched_data["tasks"].keys())[0]
            first_task = fetched_data["tasks"][first_task_title]
            if first_task:
                example["task_id"] = first_task.get("id", "task_123")
                example["project_id"] = first_task.get("projectId", "inbox123456")
        
        # Try to get first project
        if fetched_data.get("projects"):
            first_project_name = list(fetched_data["projects"].keys())[0]
            first_project = fetched_data["projects"][first_project_name]
            if first_project and "project_id" not in example:
                example["project_id"] = first_project.get("id", "inbox123456")
        
        return example
