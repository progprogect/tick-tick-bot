"""
Main application entry point
"""

import asyncio
from src.api.telegram_client import TelegramClient
from src.api.ticktick_client import TickTickClient
from src.api.openai_client import OpenAIClient
from src.services.voice_handler import VoiceHandler
from src.services.text_handler import TextHandler
from src.services.gpt_service import GPTService
from src.services.task_manager import TaskManager
from src.services.task_modifier import TaskModifier
from src.services.batch_processor import BatchProcessor
from src.services.tag_manager import TagManager
from src.services.note_manager import NoteManager
from src.services.recurring_task_manager import RecurringTaskManager
from src.services.reminder_manager import ReminderManager
from src.services.analytics_service import AnalyticsService
from src.services.project_manager import ProjectManager
from src.services.smart_router import SmartRouter
from src.models.command import ActionType
from src.utils.logger import logger
from src.utils.error_handler import format_error_message
from src.config.settings import settings


class TickTickBot:
    """Main bot application"""
    
    def __init__(self):
        """Initialize bot"""
        self.telegram_client = TelegramClient()
        self.ticktick_client = TickTickClient()
        self.openai_client = OpenAIClient()
        self.voice_handler = VoiceHandler()
        self.text_handler = TextHandler()
        self.gpt_service = GPTService(ticktick_client=self.ticktick_client)
        self.task_manager = TaskManager(self.ticktick_client)
        self.task_modifier = TaskModifier(self.ticktick_client)
        self.batch_processor = BatchProcessor(self.ticktick_client)
        self.tag_manager = TagManager(self.ticktick_client)
        self.note_manager = NoteManager(self.ticktick_client)
        self.recurring_task_manager = RecurringTaskManager(self.ticktick_client)
        self.reminder_manager = ReminderManager(self.ticktick_client)
        self.analytics_service = AnalyticsService(self.ticktick_client, self.gpt_service)
        self.project_manager = ProjectManager(self.ticktick_client)
        
        # Smart router for composite commands
        self.smart_router = SmartRouter(
            ticktick_client=self.ticktick_client,
            task_manager=self.task_manager,
            task_modifier=self.task_modifier,
            tag_manager=self.tag_manager,
            note_manager=self.note_manager,
            recurring_task_manager=self.recurring_task_manager,
            reminder_manager=self.reminder_manager,
            batch_processor=self.batch_processor,
            analytics_service=self.analytics_service,
            project_manager=self.project_manager,
        )
        
        self.logger = logger
    
    async def handle_message(self, message_text: str, user_id: str) -> str:
        """
        Handle text message
        
        Args:
            message_text: Message text
            user_id: User ID
            
        Returns:
            Response message
        """
        try:
            # Ensure client is available
            if not self.ticktick_client:
                self.logger.error("[TickTickBot] TickTick client is None in handle_message!")
                return "Ошибка: TickTick клиент не инициализирован. Попробуйте позже."
            
            # Ensure GPT service has client
            if not self.gpt_service.ticktick_client:
                self.logger.warning("[TickTickBot] GPT service lost ticktick_client reference, re-assigning...")
                self.gpt_service.ticktick_client = self.ticktick_client
            
            # Ensure client is authenticated
            if not hasattr(self.ticktick_client, 'access_token') or not self.ticktick_client.access_token:
                self.logger.info("[TickTickBot] Authenticating TickTick client...")
                await self.ticktick_client.authenticate()
            
            # Process text
            processed_text = self.text_handler.process(message_text)
            
            if not self.text_handler.validate(processed_text):
                return "Сообщение слишком длинное или пустое."
            
            # Parse command using GPT
            parsed_command = await self.gpt_service.parse_command(processed_text)
            
            # Execute command
            response = await self.execute_command(parsed_command)
            
            return response
            
        except ValueError as e:
            return str(e)
        except Exception as e:
            self.logger.error(f"Error handling message: {e}", exc_info=True)
            return format_error_message(e)
    
    async def handle_voice(self, voice_data: bytes, user_id: str) -> str:
        """
        Handle voice message
        
        Args:
            voice_data: Voice file bytes
            user_id: User ID
            
        Returns:
            Response message
        """
        try:
            # Transcribe voice to text
            text = await self.voice_handler.transcribe(voice_data)
            
            if not text:
                return "Не удалось распознать голос. Попробуйте повторить команду."
            
            # Process as text message
            return await self.handle_message(text, user_id)
            
        except Exception as e:
            self.logger.error(f"Error handling voice: {e}", exc_info=True)
            return format_error_message(e)
    
    async def execute_command(self, command) -> str:
        """
        Execute parsed command (supports both composite and legacy formats)
        
        Args:
            command: ParsedCommand object
            
        Returns:
            Response message
        """
        try:
            # Check if composite command (new format)
            if command.is_composite():
                return await self.smart_router.route(command)
            
            # Legacy format - use old routing
            action = command.action
            
            if action == ActionType.CREATE_TASK:
                return await self.task_manager.create_task(command)
            
            elif action == ActionType.UPDATE_TASK:
                return await self.task_manager.update_task(command)
            
            elif action == ActionType.DELETE_TASK:
                return await self.task_manager.delete_task(command)
            
            elif action == ActionType.COMPLETE_TASK:
                return await self.task_manager.complete_task(command)
            
            elif action == ActionType.MOVE_TASK:
                return await self.task_manager.move_task(command)
            
            elif action == ActionType.BULK_MOVE:
                # Handle bulk move
                from datetime import datetime, timedelta
                if command.period and ("вчера" in command.period.lower() or "yesterday" in command.period.lower()):
                    from_date = datetime.now() - timedelta(days=1)
                else:
                    from_date = datetime.now()
                
                to_date = datetime.now()
                
                count = await self.batch_processor.move_overdue_tasks(
                    from_date=from_date,
                    to_date=to_date,
                )
                
                return f"✓ Перенесено {count} просроченных задач на сегодня"
            
            elif action == ActionType.ADD_TAGS:
                return await self.tag_manager.add_tags(command)
            
            elif action == ActionType.BULK_ADD_TAGS:
                # Handle bulk add tags with urgency determination
                if not command.project_id:
                    return "Не указан список задач для добавления тегов"
                
                # Get tasks and determine urgency
                tasks = await self.ticktick_client.get_tasks(project_id=command.project_id)
                goals = []  # TODO: Get weekly goals if available
                
                urgency_map = await self.gpt_service.determine_urgency(tasks, goals)
                
                return await self.tag_manager.bulk_add_tags_with_urgency(
                    project_id=command.project_id,
                    urgency_map=urgency_map,
                )
            
            elif action == ActionType.ADD_NOTE:
                return await self.note_manager.add_note(command)
            
            elif action == ActionType.CREATE_RECURRING_TASK:
                return await self.recurring_task_manager.create_recurring_task(command)
            
            elif action == ActionType.SET_REMINDER:
                return await self.reminder_manager.set_reminder(command)
            
            elif action == ActionType.GET_ANALYTICS:
                period = command.period or "week"
                return await self.analytics_service.get_work_time_analytics(period)
            
            elif action == ActionType.OPTIMIZE_SCHEDULE:
                # Support period parameter
                period = command.period
                start_date = command.start_date
                end_date = command.end_date
                return await self.analytics_service.optimize_schedule(
                    period=period,
                    start_date=start_date,
                    end_date=end_date,
                )
            
            elif action == ActionType.LIST_TASKS:
                return await self.analytics_service.list_tasks(
                    start_date=command.start_date,
                    end_date=command.end_date,
                    project_id=command.project_id,
                    query_type=command.query_type,
                    limit=command.limit,
                    sort_by=command.sort_by,
                )
            
            elif action == ActionType.CREATE_PROJECT:
                return await self.project_manager.create_project(command)
            
            else:
                return f"Действие '{action}' пока не реализовано. Используйте /help для списка доступных команд."
        
        except Exception as e:
            self.logger.error(f"Error executing command: {e}", exc_info=True)
            raise
    
    async def start(self):
        """Start the bot"""
        try:
            # Validate settings
            settings.validate()
            
            # Authenticate with TickTick
            self.logger.info("Authenticating with TickTick...")
            await self.ticktick_client.authenticate()
            
            # Setup Telegram handlers
            self.telegram_client.set_message_handler(self.handle_message)
            self.telegram_client.set_voice_handler(self.handle_voice)
            
            # Start Telegram bot
            await self.telegram_client.start()
            
            self.logger.info("Bot started successfully")
            
            # Keep running
            try:
                while True:
                    await asyncio.sleep(1)
            except KeyboardInterrupt:
                self.logger.info("Received shutdown signal")
        
        except Exception as e:
            self.logger.error(f"Error starting bot: {e}", exc_info=True)
            raise
    
    async def stop(self):
        """Stop the bot"""
        self.logger.info("Stopping bot...")
        await self.telegram_client.stop()
        await self.ticktick_client.close()
        self.logger.info("Bot stopped")


async def main():
    """Main entry point"""
    bot = TickTickBot()
    
    try:
        await bot.start()
    except KeyboardInterrupt:
        await bot.stop()
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        await bot.stop()
        raise


if __name__ == "__main__":
    asyncio.run(main())

