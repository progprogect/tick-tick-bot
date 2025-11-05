"""
Telegram Bot API client
"""

from typing import Optional, Callable, Awaitable
from telegram import Update, Bot, Voice
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from telegram.error import TelegramError
from src.config.settings import settings
from src.utils.logger import logger


class TelegramClient:
    """Client for Telegram Bot API"""
    
    def __init__(self):
        """Initialize Telegram client"""
        self.token = settings.TELEGRAM_BOT_TOKEN
        self.application = Application.builder().token(self.token).build()
        self.bot = self.application.bot
        self.logger = logger
        self._message_handler: Optional[Callable[[str, str], Awaitable[str]]] = None
        self._voice_handler: Optional[Callable[[bytes, str], Awaitable[str]]] = None
    
    def set_message_handler(self, handler: Callable[[str, str], Awaitable[str]]):
        """
        Set handler for text messages
        
        Args:
            handler: Async function that takes (message_text, user_id) and returns response
        """
        self._message_handler = handler
    
    def set_voice_handler(self, handler: Callable[[bytes, str], Awaitable[str]]):
        """
        Set handler for voice messages
        
        Args:
            handler: Async function that takes (voice_data, user_id) and returns response
        """
        self._voice_handler = handler
    
    async def _handle_text(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle text messages"""
        if not self._message_handler:
            await update.message.reply_text("Text handler not configured")
            return
        
        try:
            message_text = update.message.text
            user_id = str(update.effective_user.id)
            
            self.logger.info(f"Received text message from user {user_id}: {message_text}")
            
            response = await self._message_handler(message_text, user_id)
            await update.message.reply_text(response)
            
        except Exception as e:
            self.logger.error(f"Error handling text message: {e}", exc_info=True)
            await update.message.reply_text(
                "Произошла ошибка при обработке сообщения. Попробуйте позже."
            )
    
    async def _handle_voice(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle voice messages"""
        if not self._voice_handler:
            await update.message.reply_text("Voice handler not configured")
            return
        
        try:
            voice: Voice = update.message.voice
            user_id = str(update.effective_user.id)
            
            self.logger.info(f"Received voice message from user {user_id}")
            
            # Download voice file
            voice_file = await context.bot.get_file(voice.file_id)
            voice_data = await voice_file.download_as_bytearray()
            
            response = await self._voice_handler(bytes(voice_data), user_id)
            await update.message.reply_text(response)
            
        except Exception as e:
            self.logger.error(f"Error handling voice message: {e}", exc_info=True)
            await update.message.reply_text(
                "Произошла ошибка при обработке голосового сообщения. Попробуйте позже."
            )
    
    async def _handle_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command"""
        welcome_message = (
            "👋 Привет! Я — AI-ассистент для управления задачами в TickTick!\n\n"
            "🤖 Я понимаю команды на естественном языке и могу:\n\n"
            "📝 **Управление задачами:**\n"
            "• Создавать задачи (текстом или голосом)\n"
            "• Редактировать задачи (дата, приоритет, название)\n"
            "• Удалять задачи\n"
            "• Переносить задачи между списками\n"
            "• Массовый перенос просроченных задач\n\n"
            "🏷️ **Организация:**\n"
            "• Добавлять теги к задачам\n"
            "• Добавлять заметки и описания\n"
            "• Автоматически определять срочность\n\n"
            "🔄 **Повторения и напоминания:**\n"
            "• Создавать повторяющиеся задачи (ежедневно, еженедельно)\n"
            "• Устанавливать напоминания на конкретное время\n\n"
            "📊 **Аналитика:**\n"
            "• Анализ рабочего времени\n"
            "• Оптимизация расписания\n"
            "• Просмотр задач на сегодня/неделю\n\n"
            "💬 **Как использовать:**\n"
            "Просто отправьте мне команду текстом или голосом:\n"
            "• \"Создай задачу купить молоко на завтра\"\n"
            "• \"Что у меня на сегодня?\"\n"
            "• \"Перенеси все просроченные задачи на сегодня\"\n\n"
            "Используйте /help для полного списка команд."
        )
        await update.message.reply_text(welcome_message, parse_mode='Markdown')
    
    async def _handle_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /help command"""
        help_message = (
            "👋 **Привет! Я — AI-ассистент для управления задачами в TickTick!**\n\n"
            "🤖 Я понимаю команды на естественном языке и могу:\n\n"
            "📝 **Управление задачами:**\n"
            "• Создавать задачи (текстом или голосом)\n"
            "• Редактировать задачи (дата, приоритет, название)\n"
            "• Удалять задачи\n"
            "• Переносить задачи между списками\n"
            "• Массовый перенос просроченных задач\n\n"
            "🏷️ **Организация:**\n"
            "• Добавлять теги к задачам\n"
            "• Добавлять заметки и описания\n"
            "• Автоматически определять срочность\n\n"
            "🔄 **Повторения и напоминания:**\n"
            "• Создавать повторяющиеся задачи (ежедневно, еженедельно)\n"
            "• Устанавливать напоминания на конкретное время\n\n"
            "📊 **Аналитика:**\n"
            "• Анализ рабочего времени\n"
            "• Оптимизация расписания\n"
            "• Просмотр задач на сегодня/неделю\n\n"
            "💬 **Как использовать:**\n"
            "Просто отправьте мне команду текстом или голосом:\n"
            "• \"Создай задачу купить молоко на завтра\"\n"
            "• \"Что у меня на сегодня?\"\n"
            "• \"Перенеси все просроченные задачи на сегодня\"\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "📋 **Полный список команд:**\n\n"
            "📝 **Создание задач:**\n"
            "• Создай задачу [название]\n"
            "• Добавь задачу [название] в список [название списка]\n"
            "• Создай задачу [название] на [дата]\n"
            "• Создай задачу [название] с приоритетом [высокий/средний/низкий]\n"
            "• Создай задачу [название] с тегами [тег1, тег2]\n\n"
            "✏️ **Редактирование задач:**\n"
            "• Измени задачу [название] на [дата]\n"
            "• Измени приоритет задачи [название] на [высокий]\n"
            "• Отметь задачу [название] как выполненную\n"
            "• Измени задачу [название], добавь тег [тег], перенеси на завтра\n\n"
            "🗑️ **Удаление задач:**\n"
            "• Удали задачу [название]\n"
            "• Убери из списка задачу [название]\n\n"
            "🔄 **Перенос задач:**\n"
            "• Перенеси задачу [название] в список [название]\n"
            "• Перенеси все просроченные задачи со вчера на сегодня\n"
            "• Перенеси все задачи из списка [A] в список [B]\n\n"
            "🏷️ **Управление тегами:**\n"
            "• Добавь тег [тег] к задаче [название]\n"
            "• Добавь теги [тег1, тег2] к задаче [название]\n"
            "• Добавь ко всем задачам из списка [название] теги срочности\n"
            "• Определи срочность для всех задач в списке [название]\n\n"
            "📄 **Заметки:**\n"
            "• Добавь заметку к задаче [название]: [текст]\n"
            "• Добавь описание к задаче [название]: [текст]\n\n"
            "🔄 **Повторяющиеся задачи:**\n"
            "• Создай повторяющуюся задачу [название] ежедневно\n"
            "• Создай задачу [название] каждую неделю\n"
            "• Создай задачу [название] каждые 3 дня\n\n"
            "⏰ **Напоминания:**\n"
            "• Напомни мне о задаче [название] в [время]\n"
            "• Установи напоминание на задачу [название] на завтра в 12:00\n\n"
            "📊 **Аналитика:**\n"
            "• Что у меня на сегодня?\n"
            "• Покажи мои задачи на неделю\n"
            "• Сколько за [неделя/месяц] было рабочего времени\n"
            "• Проанализируй и предложи оптимизацию расписания\n"
            "• Оптимизируй мое расписание на неделю\n\n"
            "💡 **Советы:**\n"
            "• Вы можете отправлять команды текстом или голосом\n"
            "• Я понимаю естественный язык — пишите как удобно\n"
            "• Можно комбинировать операции: \"измени задачу X, добавь тег Y, перенеси на завтра\"\n"
            "• Используйте относительные даты: сегодня, завтра, через неделю"
        )
        await update.message.reply_text(help_message, parse_mode='Markdown')
    
    def setup_handlers(self):
        """Setup message handlers"""
        # Command handlers
        self.application.add_handler(CommandHandler("start", self._handle_start))
        self.application.add_handler(CommandHandler("help", self._handle_help))
        
        # Message handlers
        self.application.add_handler(
            MessageHandler(filters.TEXT & ~filters.COMMAND, self._handle_text)
        )
        self.application.add_handler(
            MessageHandler(filters.VOICE, self._handle_voice)
        )
    
    async def send_message(self, chat_id: str, text: str) -> bool:
        """
        Send message to user
        
        Args:
            chat_id: Telegram chat ID
            text: Message text
            
        Returns:
            True if successful, False otherwise
        """
        try:
            await self.bot.send_message(chat_id=chat_id, text=text)
            return True
        except TelegramError as e:
            self.logger.error(f"Error sending message: {e}")
            return False
    
    async def start(self):
        """Start the bot"""
        self.setup_handlers()
        self.logger.info("Starting Telegram bot...")
        await self.application.initialize()
        await self.application.start()
        await self.application.updater.start_polling()
        self.logger.info("Telegram bot started and polling")
    
    async def stop(self):
        """Stop the bot"""
        self.logger.info("Stopping Telegram bot...")
        await self.application.updater.stop()
        await self.application.stop()
        await self.application.shutdown()
        self.logger.info("Telegram bot stopped")


