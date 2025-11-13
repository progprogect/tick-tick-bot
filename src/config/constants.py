"""
Application constants
"""

# Telegram Bot
TELEGRAM_MAX_MESSAGE_LENGTH = 4096
TELEGRAM_VOICE_MAX_DURATION = 60  # seconds

# OpenAI
OPENAI_DEFAULT_MODEL = "gpt-4"
OPENAI_FALLBACK_MODEL = "gpt-3.5-turbo"
OPENAI_MAX_TOKENS = 2000
OPENAI_TEMPERATURE = 0.7

# TickTick API
TICKTICK_API_BASE_URL = "https://api.ticktick.com"
TICKTICK_API_VERSION = "v1"
TICKTICK_DEFAULT_PROJECT = "Inbox"

# Task defaults
TASK_DEFAULT_PRIORITY = 0  # 0: None, 1: Low, 2: Medium, 3: High
TASK_DEFAULT_STATUS = 0  # 0: Incomplete, 1: Completed

# Batch processing
BATCH_SIZE = 10  # Number of items to process in one batch

# Retry configuration
MAX_RETRIES = 3
RETRY_DELAY = 1  # seconds

# Voice recognition
VOICE_SUPPORTED_FORMATS = ["ogg", "mp3", "m4a", "wav"]

# Logging
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

# Timezone
USER_TIMEZONE_OFFSET = 3  # UTC+3 (hours)
USER_TIMEZONE_STR = "+03:00"  # ISO format


