"""
Web interface for testing
"""

from fastapi import FastAPI, Request, Form, File, UploadFile
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pathlib import Path
import asyncio
from src.api.ticktick_client import TickTickClient
from src.api.openai_client import OpenAIClient
from src.services.voice_handler import VoiceHandler
from src.services.text_handler import TextHandler
from src.services.gpt_service import GPTService
from src.services.task_manager import TaskManager
from src.services.batch_processor import BatchProcessor
from src.services.tag_manager import TagManager
from src.services.note_manager import NoteManager
from src.services.recurring_task_manager import RecurringTaskManager
from src.services.reminder_manager import ReminderManager
from src.services.analytics_service import AnalyticsService
from src.models.command import ActionType
from src.utils.logger import logger
from src.utils.error_handler import format_error_message
from src.config.settings import settings

app = FastAPI(title="TickTick Bot Test Interface")
templates_dir = Path(__file__).parent / "templates"
templates = Jinja2Templates(directory=str(templates_dir))


class TestBot:
    """Bot instance for testing"""
    
    def __init__(self):
        self.ticktick_client = TickTickClient()
        self.openai_client = OpenAIClient()
        self.voice_handler = VoiceHandler()
        self.text_handler = TextHandler()
        self.gpt_service = GPTService()
        self.task_manager = TaskManager(self.ticktick_client)
        self.batch_processor = BatchProcessor(self.ticktick_client)
        self.tag_manager = TagManager(self.ticktick_client)
        self.note_manager = NoteManager(self.ticktick_client)
        self.recurring_task_manager = RecurringTaskManager(self.ticktick_client)
        self.reminder_manager = ReminderManager(self.ticktick_client)
        self.analytics_service = AnalyticsService(self.ticktick_client, self.gpt_service)
        self.logger = logger
    
    async def initialize(self):
        """Initialize bot clients"""
        await self.ticktick_client.authenticate()
    
    async def handle_command(self, command: str) -> str:
        """Handle test command"""
        try:
            processed_text = self.text_handler.process(command)
            
            if not self.text_handler.validate(processed_text):
                return "Сообщение слишком длинное или пустое."
            
            parsed_command = await self.gpt_service.parse_command(processed_text)
            
            action = parsed_command.action
            
            if action == ActionType.CREATE_TASK:
                return await self.task_manager.create_task(parsed_command)
            
            elif action == ActionType.UPDATE_TASK:
                return await self.task_manager.update_task(parsed_command)
            
            elif action == ActionType.DELETE_TASK:
                return await self.task_manager.delete_task(parsed_command)
            
            elif action == ActionType.MOVE_TASK:
                return await self.task_manager.move_task(parsed_command)
            
            elif action == ActionType.BULK_MOVE:
                from datetime import datetime, timedelta
                from_date = datetime.now() - timedelta(days=1)
                to_date = datetime.now()
                
                count = await self.batch_processor.move_overdue_tasks(
                    from_date=from_date,
                    to_date=to_date,
                )
                
                return f"✓ Перенесено {count} просроченных задач на сегодня"
            
            elif action == ActionType.ADD_TAGS:
                return await self.tag_manager.add_tags(parsed_command)
            
            elif action == ActionType.BULK_ADD_TAGS:
                if not parsed_command.project_id:
                    return "Не указан список задач для добавления тегов"
                
                tasks = await self.ticktick_client.get_tasks(project_id=parsed_command.project_id)
                urgency_map = await self.gpt_service.determine_urgency(tasks, [])
                
                return await self.tag_manager.bulk_add_tags_with_urgency(
                    project_id=parsed_command.project_id,
                    urgency_map=urgency_map,
                )
            
            elif action == ActionType.ADD_NOTE:
                return await self.note_manager.add_note(parsed_command)
            
            elif action == ActionType.CREATE_RECURRING_TASK:
                return await self.recurring_task_manager.create_recurring_task(parsed_command)
            
            elif action == ActionType.SET_REMINDER:
                return await self.reminder_manager.set_reminder(parsed_command)
            
            elif action == ActionType.GET_ANALYTICS:
                period = parsed_command.period or "week"
                return await self.analytics_service.get_work_time_analytics(period)
            
            elif action == ActionType.OPTIMIZE_SCHEDULE:
                # Support period parameter
                period = parsed_command.period
                start_date = parsed_command.start_date
                end_date = parsed_command.end_date
                return await self.analytics_service.optimize_schedule(
                    period=period,
                    start_date=start_date,
                    end_date=end_date,
                )
            
            elif action == ActionType.LIST_TASKS:
                return await self.analytics_service.list_tasks(
                    start_date=parsed_command.start_date,
                    end_date=parsed_command.end_date,
                    project_id=parsed_command.project_id,
                )
            
            else:
                return f"Действие '{action}' пока не реализовано."
        
        except ValueError as e:
            return str(e)
        except Exception as e:
            self.logger.error(f"Error handling command: {e}", exc_info=True)
            return format_error_message(e)
    
    async def handle_voice(self, voice_data: bytes) -> str:
        """Handle voice command"""
        try:
            text = await self.voice_handler.transcribe(voice_data)
            if not text:
                return "Не удалось распознать голос."
            return await self.handle_command(text)
        except Exception as e:
            self.logger.error(f"Error handling voice: {e}", exc_info=True)
            return format_error_message(e)


# Global bot instance
test_bot = TestBot()


@app.on_event("startup")
async def startup():
    """Initialize on startup"""
    await test_bot.initialize()
    logger.info("Test bot initialized")


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """Main page"""
    return templates.TemplateResponse("index.html", {"request": request})


@app.post("/api/command")
async def process_command(command: str = Form(...)):
    """Process text command"""
    try:
        response = await test_bot.handle_command(command)
        return {"success": True, "message": response}
    except Exception as e:
        logger.error(f"Error processing command: {e}", exc_info=True)
        error_msg = str(e)
        
        # Provide more user-friendly error messages for common API errors
        if "500" in error_msg and "api.ticktick.com" in error_msg:
            return {
                "success": False,
                "message": "⚠️ TickTick API временно недоступен или не поддерживает эту операцию. Попробуйте позже или используйте другой способ."
            }
        elif "403" in error_msg and "api.ticktick.com" in error_msg:
            return {
                "success": False,
                "message": "⚠️ Нет доступа к TickTick API. Проверьте настройки авторизации."
            }
        elif "404" in error_msg:
            return {
                "success": False,
                "message": "⚠️ Задача не найдена. Убедитесь, что задача существует."
            }
        else:
            return {"success": False, "message": format_error_message(e)}


@app.post("/api/voice")
async def process_voice(file: UploadFile = File(...)):
    """Process voice command"""
    try:
        voice_data = await file.read()
        response = await test_bot.handle_voice(voice_data)
        return {"success": True, "message": response}
    except Exception as e:
        logger.error(f"Error processing voice: {e}", exc_info=True)
        return {"success": False, "message": format_error_message(e)}


@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=settings.WEB_PORT)

