# Credentials and Access Information
## Telegram Bot для управления TickTick

**Версия:** 1.0  
**Дата:** 2024-11-04  
**Статус:** Active

---

## ⚠️ ВАЖНО: Безопасность

**Этот документ содержит чувствительные данные.**
- Не коммитьте этот файл в публичный репозиторий
- Используйте `.env` файл для локальной разработки
- Добавьте `credentials.md` в `.gitignore` если храните реальные данные

---

## Telegram Bot

**Bot Username:** `@TickTick_My_bot`  
**Bot Token:** `7008534039:AAFew6otgYEhLSYS4hYlnzZfFDsjTRMRPPk`

**Описание:**
- Бот для управления задачами TickTick через Telegram
- Поддержка голосовых и текстовых команд
- Интеграция с OpenAI GPT для понимания естественного языка

**Документация:**
- [Telegram Bot API](https://core.telegram.org/bots/api)
- [BotFather](https://t.me/BotFather)

---

## OpenAI API

**API Key:** `<YOUR_OPENAI_API_KEY>`

**Использование:**
- GPT-4 для парсинга команд пользователя
- Whisper API для распознавания голоса (опционально)
- Модель: `gpt-4` или `gpt-3.5-turbo` (по умолчанию)

**Документация:**
- [OpenAI API Documentation](https://platform.openai.com/docs)
- [OpenAI Python SDK](https://github.com/openai/openai-python)

**Ограничения:**
- Rate limits зависят от плана OpenAI
- Мониторьте использование токенов

---

## TickTick API

**Email:** `progprogect@gmail.com`  
**Password:** `muwhi6-fiBdef-hoqpof`

**Access Token:**
- Токен доступа: `tp_129f30f9ec524ded813233f2e4b94083`
- Используется для прямого доступа к API без OAuth flow

**OAuth 2.0 Credentials (опционально):**
- Client ID: *Получить из [TickTick Developer Portal](https://developer.ticktick.com/)*
- Client Secret: *Получить из TickTick Developer Portal*

**Документация:**
- [TickTick OpenAPI Documentation](https://developer.ticktick.com/docs#/openapi)
- [Developer Portal](https://developer.ticktick.com/)

**Для получения Client ID и Client Secret:**
1. Зарегистрируйтесь на [TickTick Developer Portal](https://developer.ticktick.com/)
2. Создайте новое приложение
3. Получите `client_id` и `client_secret`
4. Добавьте их в `.env` файл

**API Endpoints:**
- Base URL: `https://api.ticktick.com`
- Authentication: OAuth 2.0
- Основные endpoints:
  - `POST /open/v1/task` - создание задачи
  - `PUT /open/v1/task/{task_id}` - обновление задачи
  - `DELETE /open/v1/task/{task_id}` - удаление задачи
  - `GET /open/v1/task` - получение списка задач
  - `POST /open/v1/task/{task_id}/tag` - добавление тегов
  - `POST /open/v1/task/{task_id}/reminder` - установка напоминаний

---

## Конфигурация переменных окружения

Создайте файл `.env` в корне проекта со следующим содержимым:

```env
# Telegram Bot
TELEGRAM_BOT_TOKEN=7008534039:AAFew6otgYEhLSYS4hYlnzZfFDsjTRMRPPk

# OpenAI
OPENAI_API_KEY=<YOUR_OPENAI_API_KEY>

# TickTick
TICKTICK_EMAIL=progprogect@gmail.com
TICKTICK_PASSWORD=muwhi6-fiBdef-hoqpof
TICKTICK_ACCESS_TOKEN=tp_129f30f9ec524ded813233f2e4b94083
TICKTICK_CLIENT_ID=<опционально, получить из TickTick Developer Portal>
TICKTICK_CLIENT_SECRET=<опционально, получить из TickTick Developer Portal>

# Database
DATABASE_URL=sqlite:///./ticktick_bot.db

# Application
LOG_LEVEL=INFO
WEB_PORT=8000
```

---

## Проверка доступа

### Telegram Bot
```bash
curl https://api.telegram.org/bot7008534039:AAFew6otgYEhLSYS4hYlnzZfFDsjTRMRPPk/getMe
```

### OpenAI API
```bash
curl https://api.openai.com/v1/models \
  -H "Authorization: Bearer <YOUR_OPENAI_API_KEY>"
```

### TickTick API
После получения Client ID и Client Secret, используйте OAuth 2.0 flow для получения access_token.

---

## История изменений

| Дата | Автор | Описание |
|------|-------|----------|
| 2024-11-04 | System Architect | Первоначальная версия документации |

---

## Примечания

- Все токены и пароли должны храниться в переменных окружения
- Не коммитьте реальные credentials в репозиторий
- Регулярно обновляйте токены при необходимости
- Мониторьте использование API для предотвращения превышения лимитов

