"""
OpenAI API client
"""

import json
import re
from datetime import datetime
from typing import Optional, Dict, Any, List
from openai import AsyncOpenAI
from src.config.settings import settings
from src.config.constants import (
    OPENAI_DEFAULT_MODEL,
    OPENAI_FALLBACK_MODEL,
    OPENAI_MAX_TOKENS,
    OPENAI_TEMPERATURE,
)
from src.utils.logger import logger


class OpenAIClient:
    """Client for OpenAI API"""
    
    def __init__(self):
        """Initialize OpenAI client"""
        self.api_key = settings.OPENAI_API_KEY
        self.client = AsyncOpenAI(api_key=self.api_key)
        self.model = OPENAI_DEFAULT_MODEL
        self.fallback_model = OPENAI_FALLBACK_MODEL
        self.logger = logger
    
    async def chat_completion(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: float = OPENAI_TEMPERATURE,
        max_tokens: int = OPENAI_MAX_TOKENS,
    ) -> str:
        """
        Get chat completion from OpenAI
        
        Args:
            messages: List of message dictionaries with 'role' and 'content'
            model: Model to use (defaults to configured model)
            temperature: Sampling temperature
            max_tokens: Maximum tokens in response
            
        Returns:
            Response text
            
        Raises:
            Exception: If API call fails
        """
        model = model or self.model
        
        try:
            self.logger.debug(f"Calling OpenAI API with model {model}")
            
            response = await self.client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            
            content = response.choices[0].message.content
            self.logger.debug(f"OpenAI API response: {content[:100]}...")
            
            return content
            
        except Exception as e:
            self.logger.error(f"OpenAI API error: {e}")
            
            # Try fallback model if main model fails
            if model != self.fallback_model:
                self.logger.warning(f"Trying fallback model {self.fallback_model}")
                return await self.chat_completion(
                    messages=messages,
                    model=self.fallback_model,
                    temperature=temperature,
                    max_tokens=max_tokens,
                )
            
            raise
    
    async def transcribe_audio(
        self,
        audio_data: bytes,
        filename: str = "audio.ogg",
    ) -> str:
        """
        Transcribe audio using Whisper API
        
        Args:
            audio_data: Audio file bytes
            filename: Audio file name with extension
            
        Returns:
            Transcribed text
            
        Raises:
            Exception: If transcription fails
        """
        try:
            self.logger.debug(f"Transcribing audio file: {filename}")
            
            # Save audio to temporary file
            import tempfile
            import os
            
            with tempfile.NamedTemporaryFile(delete=False, suffix=f".{filename.split('.')[-1]}") as tmp_file:
                tmp_file.write(audio_data)
                tmp_file_path = tmp_file.name
            
            try:
                with open(tmp_file_path, "rb") as audio_file:
                    transcript = await self.client.audio.transcriptions.create(
                        model="whisper-1",
                        file=audio_file,
                    )
                
                text = transcript.text
                self.logger.debug(f"Transcribed text: {text}")
                
                return text
            finally:
                if os.path.exists(tmp_file_path):
                    os.unlink(tmp_file_path)
            
        except Exception as e:
            self.logger.error(f"Whisper API error: {e}")
            raise
    
    async def parse_command(
        self,
        command: str,
        system_prompt: Optional[str] = None,
        context_info: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Parse user command using GPT
        
        Args:
            command: User command text
            system_prompt: System prompt for GPT (optional)
            
        Returns:
            Parsed command as dictionary
            
        Raises:
            Exception: If parsing fails
        """
        if system_prompt is None:
            system_prompt = (
                "Ты - AI-ассистент для управления задачами в TickTick. "
                "Пользователь отправляет команду на естественном языке. "
                "Твоя задача - определить действие и параметры задачи. "
                "Верни ТОЛЬКО валидный JSON с полями: "
                "action (create_task, update_task, delete_task, move_task, add_tags, add_note, create_recurring_task, set_reminder, get_analytics, optimize_schedule), "
                "title (название задачи), "
                "projectId (ID списка, опционально), "
                "dueDate (дата в формате ISO 8601, опционально), "
                "priority (0-3, опционально), "
                "tags (массив строк, опционально), "
                "notes (текст заметки, опционально), "
                "targetProjectId (ID целевого списка для переноса, опционально), "
                "recurrence (объект с полями: type, interval, опционально), "
                "reminder (дата и время в формате ISO 8601, опционально), "
                "period (период для аналитики, опционально). "
                "Если команда неоднозначна, верни JSON с полем 'error' и сообщением."
            )
        
        # Add current date to system prompt
        current_date = datetime.now().strftime("%Y-%m-%d")
        current_datetime = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        date_context = f"\n\nВАЖНО: Сегодня - {current_date} ({current_datetime}). Используй эту дату для определения относительных дат (сегодня, завтра, на следующей неделе и т.д.)."
        
        # Add context information (projects only) if available
        context_text = ""
        if context_info and context_info.get("projects"):
            projects_list = context_info["projects"]
            projects_text = "\n".join([
                f"  - {p.get('name', '')} (ID: {p.get('id', '')}, поиск: '{p.get('name_clean', p.get('name', ''))}')"
                for p in projects_list
            ])
            context_text = f"\n\nДОСТУПНЫЕ СПИСКИ ПРОЕКТОВ:\n{projects_text}\n\nКРИТИЧЕСКИ ВАЖНО - ИСПОЛЬЗОВАНИЕ PROJECT ID:\n- При создании задачи (create_task) - ВСЕГДА используй projectId из списка выше, если пользователь указывает список (например, 'в списке Работа', 'в проекте Работа', 'в Работа')\n- При обновлении задачи (update_task) - если нужно изменить список задачи, используй projectId из списка выше\n- При переносе задачи (move_task) - используй targetProjectId из списка выше\n- При указании списка в команде используй ТОЧНЫЙ ID из списка выше, НЕ название\n- АЛГОРИТМ: Если пользователь говорит 'в списке Работа' или 'в проекте Работа' или 'в Работа', найди проект в списке выше, который соответствует 'Работа' (проверяй поле 'поиск' или название без эмодзи). Если проект называется '💼Работа' (поиск: 'Работа'), то используй его ID для 'Работа'\n- ПРИМЕР: Команда 'Создай задачу X в списке Работа' → найди в списке выше проект с name='Работа', возьми его ID и используй в projectId\n- ПРИМЕР: Команда 'Создай задачу просто тестовая задача в списке Работа' → title='просто тестовая задача', projectId='ID_ПРОЕКТА_РАБОТА_ИЗ_КОНТЕКСТА'\n- ВАЖНО: Фразы 'в списке X', 'в проекте X', 'в X' ВСЕГДА указывают на проект - НЕ включай их в название задачи!\n- Если проект не найден в списке, верни JSON с полем 'error' и сообщением"
        
        enhanced_system_prompt = system_prompt + date_context + context_text
        
        messages = [
            {"role": "system", "content": enhanced_system_prompt},
            {"role": "user", "content": command},
        ]
        
        try:
            response = await self.chat_completion(messages=messages)
            
            # Parse JSON from response
            # Extract JSON from response (in case GPT adds extra text)
            # Try to find JSON object or array
            json_match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', response, re.DOTALL)
            if not json_match:
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
                parsed = json.loads(json_str)
                self.logger.debug(f"Parsed command: {parsed}")
                return parsed
            except json.JSONDecodeError as e:
                self.logger.error(f"Failed to parse JSON: {json_str}")
                self.logger.error(f"JSON decode error: {e}")
                # Try to extract action and title manually
                if "create_task" in response.lower() or "создай" in response.lower():
                    title_match = re.search(r'"title"\s*:\s*"([^"]+)"', response)
                    if title_match:
                        return {
                            "action": "create_task",
                            "title": title_match.group(1)
                        }
                raise ValueError(f"Не удалось распарсить ответ GPT: {json_str}")
            
        except json.JSONDecodeError as e:
            self.logger.error(f"Failed to parse JSON from GPT response: {e}")
            raise ValueError(f"Не удалось распарсить команду: {e}")
        except Exception as e:
            self.logger.error(f"Error parsing command: {e}")
            raise

