"""
GPT service for parsing commands
"""

import json
import re
from typing import Dict, Any, Optional
from src.api.openai_client import OpenAIClient
from src.services.prompt_manager import PromptManager
from src.models.command import ParsedCommand
from src.utils.logger import logger


class GPTService:
    """Service for parsing commands using GPT"""
    
    def __init__(self):
        """Initialize GPT service"""
        self.openai_client = OpenAIClient()
        self.prompt_manager = PromptManager()
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
            
            parsed_dict = await self.openai_client.parse_command(
                command=command,
                system_prompt=system_prompt,
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
