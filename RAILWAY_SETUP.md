# Инструкция по настройке Railway

## Переменные окружения для Railway

В Railway Dashboard → Ваш проект → Variables нужно добавить следующие переменные:

### Обязательные переменные:

1. **TELEGRAM_BOT_TOKEN**
   - Описание: Токен Telegram бота
   - Пример: `1234567890:ABCdefGHIjklMNOpqrsTUVwxyz`
   - Где взять: [BotFather](https://t.me/BotFather) в Telegram

2. **OPENAI_API_KEY**
   - Описание: API ключ OpenAI для GPT
   - Пример: `sk-proj-...`
   - Где взять: [OpenAI Platform](https://platform.openai.com/api-keys)

3. **TICKTICK_EMAIL**
   - Описание: Email аккаунта TickTick
   - Пример: `your_email@example.com`

4. **TICKTICK_PASSWORD**
   - Описание: Пароль аккаунта TickTick
   - Пример: `your_password`

5. **TICKTICK_ACCESS_TOKEN**
   - Описание: Токен доступа TickTick API
   - Пример: `tp_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx`
   - Где взять: TickTick Developer Portal или через API

### Опциональные переменные:

6. **TICKTICK_CLIENT_ID** (опционально)
   - Описание: Client ID для OAuth 2.0
   - Где взять: [TickTick Developer Portal](https://developer.ticktick.com/)

7. **TICKTICK_CLIENT_SECRET** (опционально)
   - Описание: Client Secret для OAuth 2.0
   - Где взять: TickTick Developer Portal

8. **CACHE_FILE_PATH** (опционально)
   - Описание: Путь к файлу кэша
   - По умолчанию: `/tmp/task_cache.json`
   - Рекомендуется: оставить по умолчанию для временного хранилища

9. **LOG_LEVEL** (опционально)
   - Описание: Уровень логирования
   - По умолчанию: `INFO`
   - Варианты: `DEBUG`, `INFO`, `WARNING`, `ERROR`

10. **USE_WHISPER** (опционально)
    - Описание: Использовать Whisper для распознавания голоса
    - По умолчанию: `false`
    - Варианты: `true`, `false`

## Как добавить переменные в Railway:

1. Откройте ваш проект в [Railway Dashboard](https://railway.app/)
2. Перейдите в раздел **Variables**
3. Нажмите **+ New Variable**
4. Введите **Name** (имя переменной) и **Value** (значение)
5. Нажмите **Add**

## Пример заполнения:

```
TELEGRAM_BOT_TOKEN = your_telegram_bot_token_here
OPENAI_API_KEY = sk-proj-your_openai_api_key_here
TICKTICK_EMAIL = your_email@example.com
TICKTICK_PASSWORD = your_password_here
TICKTICK_ACCESS_TOKEN = tp_your_access_token_here
LOG_LEVEL = INFO
CACHE_FILE_PATH = /tmp/task_cache.json
```

## Важные замечания:

- ⚠️ **Не коммитьте реальные значения в репозиторий!**
- ✅ Все секреты храните только в Railway Variables
- ✅ Файл `.env.example` содержит только шаблоны без реальных значений
- ✅ Кэш хранится во временной файловой системе (`/tmp`), данные теряются при перезапуске контейнера

## После настройки:

1. Railway автоматически соберет проект на основе `requirements.txt`
2. Запустит бота используя `Procfile`
3. Бот будет работать 24/7 и автоматически перезапускаться при ошибках

## Проверка работы:

После деплоя проверьте логи в Railway Dashboard → Deployments → View Logs
Должны увидеть сообщение: "Bot started successfully"

