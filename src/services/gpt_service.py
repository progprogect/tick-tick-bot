"""
GPT service for parsing commands
"""

import json
import re
from typing import Dict, Any, Optional
from src.api.openai_client import OpenAIClient
from src.api.ticktick_client import TickTickClient
from src.services.prompt_manager import PromptManager
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
        Parse user command using GPT
        
        Args:
            command: User command text
            
        Returns:
            ParsedCommand object
            
        Raises:
            ValueError: If parsing fails
        """
        try:
            self.logger.debug(f"Parsing command: {command}")
            
            system_prompt = self.prompt_manager.get_system_prompt()
            
            # Get context (projects only) before parsing
            context_info = await self._get_context_for_parsing()
            
            parsed_dict = await self.openai_client.parse_command(
                command=command,
                system_prompt=system_prompt,
                context_info=context_info,
            )
            
            # Check for errors
            if "error" in parsed_dict:
                error_msg = parsed_dict["error"]
                self.logger.warning(f"GPT returned error: {error_msg}")
                raise ValueError(error_msg)
            
            # Create ParsedCommand object
            parsed_command = ParsedCommand(**parsed_dict)
            
            self.logger.debug(f"Parsed command: {parsed_command}")
            
            return parsed_command
            
        except Exception as e:
            self.logger.error(f"Error parsing command: {e}", exc_info=True)
            raise ValueError(f"Не удалось обработать команду: {str(e)}")
    
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
            return context
        
        try:
            # Get projects list only
            projects = await self.ticktick_client.get_projects()
            context["projects"] = [
                {
                    "id": p.get("id", ""),
                    "name": p.get("name", ""),
                }
                for p in projects
            ]
            self.logger.debug(f"Retrieved {len(context['projects'])} projects for context")
            
        except Exception as e:
            self.logger.warning(f"Failed to get context for parsing: {e}")
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
