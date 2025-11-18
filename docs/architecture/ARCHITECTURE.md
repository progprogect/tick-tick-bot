# Архитектура системы
## Telegram Bot для управления TickTick

**Дата:** 2024-11-04  
**Версия:** 1.0

---

## Обзор архитектуры

Система построена по модульной архитектуре с четким разделением ответственности:

```
Пользователь → Telegram/Web → Text/Voice Handler → GPT Service → Command Router → Service Layer → TickTick API
```

---

## Поток обработки запроса

### 1. Входная точка (Entry Point)

**Web Interface** (`src/web/main.py`):
```python
@app.post("/api/command")
async def process_command(command: str = Form(...)):
    response = await test_bot.handle_command(command)
    return {"success": True, "message": response}
```

**Telegram Bot** (`src/main.py`):
```python
async def handle_message(self, message_text: str, user_id: str) -> str:
    processed_text = self.text_handler.process(message_text)
    parsed_command = await self.gpt_service.parse_command(processed_text)
    response = await self.execute_command(parsed_command)
    return response
```

---

### 2. Обработка текста (Text Handler)

**Класс:** `TextHandler` (`src/services/text_handler.py`)

**Функции:**
- Очистка текста (удаление лишних пробелов)
- Валидация (проверка длины, непустота)

**Пример:**
```python
processed_text = self.text_handler.process("Создай задачу купить молоко")
# Результат: "Создай задачу купить молоко" (нормализованный)
```

---

### 3. Парсинг команды через GPT (GPT Service)

**Класс:** `GPTService` (`src/services/gpt_service.py`)

**Процесс:**
1. Получение системного промпта из `PromptManager`
2. Отправка команды в OpenAI API через `OpenAIClient`
3. Получение JSON ответа от GPT
4. Парсинг JSON в `ParsedCommand` объект

**Системный промпт** (`src/services/prompt_manager.py`):
```
Ты - AI-ассистент для управления задачами в TickTick.
Пользователь отправляет команду на естественном языке.
Твоя задача - определить действие и параметры задачи.

Доступные действия:
- create_task: Создание новой задачи
- update_task: Обновление существующей задачи
- delete_task: Удаление задачи
- move_task: Перенос задачи между списками
- add_tags: Добавление тегов к задаче
- add_note: Добавление заметки к задаче
...
```

**Пример команды:**
```
"Создай задачу купить молоко на завтра"
```

**Результат GPT:**
```json
{
  "action": "create_task",
  "title": "купить молоко",
  "dueDate": "2024-11-05T00:00:00+00:00"
}
```

**Объект ParsedCommand:**
```python
ParsedCommand(
    action=ActionType.CREATE_TASK,
    title="купить молоко",
    due_date="2024-11-05T00:00:00+00:00"
)
```

---

### 4. Маршрутизация команд (Command Router)

**Класс:** `TestBot` или `TickTickBot` (`src/web/main.py` или `src/main.py`)

**Логика маршрутизации:**
```python
async def handle_command(self, command: str) -> str:
    # 1. Обработка текста
    processed_text = self.text_handler.process(command)
    
    # 2. Парсинг через GPT
    parsed_command = await self.gpt_service.parse_command(processed_text)
    
    # 3. Маршрутизация по action
    action = parsed_command.action
    
    if action == ActionType.CREATE_TASK:
        return await self.task_manager.create_task(parsed_command)
    
    elif action == ActionType.UPDATE_TASK:
        return await self.task_manager.update_task(parsed_command)
    
    elif action == ActionType.DELETE_TASK:
        return await self.task_manager.delete_task(parsed_command)
    
    elif action == ActionType.MOVE_TASK:
        return await self.task_manager.move_task(parsed_command)
    
    elif action == ActionType.ADD_TAGS:
        return await self.tag_manager.add_tags(parsed_command)
    
    elif action == ActionType.ADD_NOTE:
        return await self.note_manager.add_note(parsed_command)
    
    # ... и т.д.
```

**Доступные ActionType:**
```python
class ActionType(str, Enum):
    CREATE_TASK = "create_task"
    UPDATE_TASK = "update_task"
    DELETE_TASK = "delete_task"
    MOVE_TASK = "move_task"
    ADD_TAGS = "add_tags"
    ADD_NOTE = "add_note"
    CREATE_RECURRING_TASK = "create_recurring_task"
    SET_REMINDER = "set_reminder"
    GET_ANALYTICS = "get_analytics"
    OPTIMIZE_SCHEDULE = "optimize_schedule"
    BULK_MOVE = "bulk_move"
    BULK_ADD_TAGS = "bulk_add_tags"
```

---

### 5. Сервисный слой (Service Layer)

Каждый сервис отвечает за свою область функциональности:

#### 5.1. TaskManager (`src/services/task_manager.py`)

**Ответственность:** Управление задачами (CRUD операции)

**Методы:**
- `create_task()` - создание задачи
- `update_task()` - обновление задачи
- `delete_task()` - удаление задачи
- `move_task()` - перенос задачи между списками

**Пример:**
```python
async def create_task(self, command: ParsedCommand) -> str:
    # 1. Валидация параметров
    if not command.title:
        raise ValueError("Название задачи не указано")
    
    # 2. Парсинг даты
    due_date = parse_date(command.due_date) if command.due_date else None
    
    # 3. Вызов TickTick API
    task_data = await self.client.create_task(
        title=command.title,
        project_id=command.project_id,
        due_date=due_date,
        priority=command.priority,
        tags=command.tags,
        notes=command.notes,
    )
    
    # 4. Сохранение в кэш
    self.cache.save_task(
        task_id=task_data.get("id"),
        title=command.title,
        project_id=command.project_id,
    )
    
    # 5. Форматирование ответа
    return format_task_created(task_data)
```

#### 5.2. TagManager (`src/services/tag_manager.py`)

**Ответственность:** Управление тегами

**Методы:**
- `add_tags()` - добавление тегов к задаче
- `bulk_add_tags_with_urgency()` - массовое добавление тегов

**Пример:**
```python
async def add_tags(self, command: ParsedCommand) -> str:
    # 1. Поиск задачи в кэше
    task_id = self.cache.get_task_id_by_title(command.title)
    
    # 2. Получение текущих тегов
    original_task_data = self.cache.get_task_data(task_id)
    existing_tags = original_task_data.get('tags', [])
    
    # 3. Объединение тегов
    merged_tags = list(set(existing_tags + command.tags))
    
    # 4. Обновление через TickTick API
    await self.client.update_task(
        task_id=task_id,
        tags=merged_tags,
    )
    
    return f"✓ Теги добавлены к задаче: {', '.join(command.tags)}"
```

#### 5.3. NoteManager (`src/services/note_manager.py`)

**Ответственность:** Управление заметками

**Методы:**
- `add_note()` - добавление заметки к задаче

#### 5.4. BatchProcessor (`src/services/batch_processor.py`)

**Ответственность:** Массовые операции

**Методы:**
- `move_overdue_tasks()` - массовый перенос просроченных задач

#### 5.5. Другие сервисы:
- `RecurringTaskManager` - повторяющиеся задачи
- `ReminderManager` - напоминания
- `AnalyticsService` - аналитика
- `VoiceHandler` - обработка голосовых сообщений

---

### 6. API Клиенты (API Clients)

#### 6.1. TickTickClient (`src/api/ticktick_client.py`)

**Ответственность:** Интеграция с TickTick OpenAPI

**Методы:**
```python
async def create_task(...) -> Dict[str, Any]
async def update_task(...) -> Dict[str, Any]
async def delete_task(...) -> bool
async def complete_task(...) -> bool
async def get_tasks(...) -> List[Dict[str, Any]]
```

**Пример запроса:**
```python
async def create_task(
    self,
    title: str,
    project_id: Optional[str] = None,
    due_date: Optional[str] = None,
    priority: int = 0,
    tags: Optional[List[str]] = None,
    notes: Optional[str] = None,
) -> Dict[str, Any]:
    # 1. Подготовка данных
    task_data = {
        "title": title,
        "status": 0,  # Active
    }
    if project_id:
        task_data["projectId"] = project_id
    if due_date:
        task_data["dueDate"] = due_date
    # ... и т.д.
    
    # 2. Отправка запроса
    response = await self.post(
        endpoint=f"/open/{TICKTICK_API_VERSION}/task",
        headers=self._get_headers(),
        json_data=task_data,
    )
    
    return response
```

**Endpoints TickTick API:**
- `POST /open/v1/task` - создание задачи
- `POST /open/v1/task/{taskId}` - обновление задачи
- `DELETE /open/v1/project/{projectId}/task/{taskId}` - удаление задачи
- `POST /open/v1/project/{projectId}/task/{taskId}/complete` - завершение задачи
- `GET /open/v1/task` - получение списка задач (может не работать)

#### 6.2. OpenAIClient (`src/api/openai_client.py`)

**Ответственность:** Интеграция с OpenAI API

**Методы:**
- `parse_command()` - парсинг команды через GPT
- `chat_completion()` - общий метод для GPT запросов
- `transcribe_audio()` - распознавание голоса через Whisper

#### 6.3. TelegramClient (`src/api/telegram_client.py`)

**Ответственность:** Интеграция с Telegram Bot API

**Методы:**
- Обработка сообщений
- Обработка голосовых сообщений
- Отправка ответов

---

### 7. Кэш задач (Task Cache)

**Класс:** `TaskCacheService` (`src/services/task_cache.py`)

**Назначение:** Хранение соответствия task_id ↔ title для задач, созданных через бота

**Проблема:** TickTick API GET `/open/v1/task` не работает, поэтому невозможно найти задачу по названию через API.

**Решение:** Кэширование задач при создании.

**Структура кэша:**
```json
{
  "task_id_123": {
    "title": "купить молоко",
    "project_id": "inbox123",
    "status": "active",
    "created_at": "2024-11-04T10:00:00",
    "updated_at": "2024-11-04T10:00:00"
  }
}
```

**Методы:**
- `save_task()` - сохранение задачи в кэш
- `get_task_id_by_title()` - поиск task_id по названию
- `get_task_data()` - получение данных задачи
- `delete_task()` - удаление из кэша
- `mark_as_completed()` - пометка как завершенной

---

## Диаграмма потока данных

```
┌─────────────┐
│  Пользователь │
└──────┬───────┘
       │ "Создай задачу купить молоко"
       ▼
┌─────────────────┐
│  Web/Telegram   │
│   Interface     │
└──────┬──────────┘
       │
       ▼
┌─────────────────┐
│  TextHandler    │  Обработка и валидация текста
└──────┬──────────┘
       │
       ▼
┌─────────────────┐
│   GPTService    │  Парсинг через OpenAI GPT
│                 │  → ParsedCommand(action="create_task", title="купить молоко")
└──────┬──────────┘
       │
       ▼
┌─────────────────┐
│  Command Router │  Маршрутизация по action
│  (handle_command)│  → ActionType.CREATE_TASK
└──────┬──────────┘
       │
       ▼
┌─────────────────┐
│  TaskManager    │  Бизнес-логика создания задачи
│  (create_task)  │
└──────┬──────────┘
       │
       ├─────────────────┐
       ▼                 ▼
┌──────────────┐  ┌──────────────┐
│ TickTickClient│  │ TaskCache    │
│ (create_task)│  │ (save_task)  │
└──────┬───────┘  └──────────────┘
       │
       ▼
┌──────────────┐
│ TickTick API │  POST /open/v1/task
│              │  → {id: "task_123", title: "купить молоко", ...}
└──────┬───────┘
       │
       ▼
┌──────────────┐
│  Форматирование│  format_task_created()
│  Ответа       │  → "✓ Задача 'купить молоко' создана в списке inbox123"
└──────┬───────┘
       │
       ▼
┌──────────────┐
│  Пользователь │
└──────────────┘
```

---

## Как определяется, куда отправлять запрос

### 1. Определение действия (Action)

**GPT определяет action** на основе команды пользователя:

```
"Создай задачу купить молоко" → action: "create_task"
"Измени задачу купить молоко" → action: "update_task"
"Удали задачу купить молоко" → action: "delete_task"
"Добавь тег важное к задаче купить молоко" → action: "add_tags"
```

**Процесс:**
1. GPT получает системный промпт с описанием всех доступных действий
2. GPT анализирует команду пользователя
3. GPT возвращает JSON с полем `action` и параметрами

### 2. Маршрутизация по ActionType

**Command Router** использует `if-elif` цепочку для выбора нужного сервиса:

```python
if action == ActionType.CREATE_TASK:
    return await self.task_manager.create_task(parsed_command)
elif action == ActionType.UPDATE_TASK:
    return await self.task_manager.update_task(parsed_command)
# ... и т.д.
```

### 3. Выбор API endpoint

**Каждый сервис знает, какой endpoint использовать:**

- `TaskManager.create_task()` → `POST /open/v1/task`
- `TaskManager.update_task()` → `POST /open/v1/task/{taskId}`
- `TaskManager.delete_task()` → `DELETE /open/v1/project/{projectId}/task/{taskId}`
- `TagManager.add_tags()` → `POST /open/v1/task/{taskId}` (с полем `tags`)
- `NoteManager.add_note()` → `POST /open/v1/task/{taskId}` (с полем `content`)

### 4. Получение projectId

**Проблема:** Некоторые endpoints требуют `projectId` в пути URL.

**Решение:**
- Если `projectId` указан в команде → используется
- Если не указан → берется из кэша (`TaskCacheService`)
- Если не найден в кэше → ошибка с понятным сообщением

**Пример:**
```python
# В update_task
if "projectId" not in task_data:
    from src.services.task_cache import TaskCacheService
    cache = TaskCacheService()
    cached_task = cache.get_task_data(task_id)
    if cached_task and cached_task.get('project_id'):
        task_data["projectId"] = cached_task.get('project_id')
```

---

## Ключевые компоненты

### 1. Модели данных

**ParsedCommand** (`src/models/command.py`):
```python
class ParsedCommand(BaseModel):
    action: ActionType
    title: Optional[str] = None
    task_id: Optional[str] = None
    project_id: Optional[str] = None
    due_date: Optional[str] = None
    priority: Optional[int] = None
    tags: Optional[List[str]] = None
    notes: Optional[str] = None
    # ... и т.д.
```

### 2. Утилиты

- **date_parser** - парсинг дат из естественного языка
- **formatters** - форматирование сообщений для пользователя
- **logger** - логирование
- **error_handler** - обработка ошибок

### 3. Конфигурация

- **settings** - настройки из .env файла
- **constants** - константы (URL, версии API и т.д.)

---

## Преимущества архитектуры

1. **Модульность:** Каждый сервис отвечает за свою область
2. **Расширяемость:** Легко добавить новый action или сервис
3. **Тестируемость:** Каждый компонент можно тестировать отдельно
4. **Читаемость:** Понятный поток данных
5. **Разделение ответственности:** Каждый слой делает свою работу

---

## Примеры потоков

### Пример 1: Создание задачи

```
1. Пользователь: "Создай задачу купить молоко на завтра"
2. TextHandler: валидация и нормализация
3. GPTService: парсинг → {action: "create_task", title: "купить молоко", dueDate: "2024-11-05"}
4. Command Router: action == CREATE_TASK → TaskManager.create_task()
5. TaskManager: парсинг даты, подготовка данных
6. TickTickClient: POST /open/v1/task с данными задачи
7. TaskCache: сохранение task_id → title в кэш
8. Formatter: форматирование ответа
9. Пользователь: "✓ Задача 'купить молоко' создана в списке inbox123"
```

### Пример 2: Обновление задачи

```
1. Пользователь: "Измени задачу купить молоко на завтра"
2. TextHandler: валидация
3. GPTService: парсинг → {action: "update_task", title: "купить молоко", dueDate: "2024-11-05"}
4. Command Router: action == UPDATE_TASK → TaskManager.update_task()
5. TaskManager: поиск task_id в кэше по названию "купить молоко"
6. TaskManager: получение projectId из кэша
7. TaskManager: подготовка update_data {dueDate: "2024-11-05"}
8. TickTickClient: POST /open/v1/task/{taskId} с update_data
9. Formatter: форматирование ответа с указанием изменений
10. Пользователь: "✓ Задача 'купить молоко' обновлена: дата изменена на 05.11.2024"
```

### Пример 3: Добавление тегов

```
1. Пользователь: "Добавь тег важное к задаче купить молоко"
2. TextHandler: валидация
3. GPTService: парсинг → {action: "add_tags", title: "купить молоко", tags: ["важное"]}
4. Command Router: action == ADD_TAGS → TagManager.add_tags()
5. TagManager: поиск task_id в кэше по названию "купить молоко"
6. TagManager: получение текущих тегов из кэша
7. TagManager: объединение тегов (существующие + новые)
8. TickTickClient: POST /open/v1/task/{taskId} с полем tags
9. Пользователь: "✓ Теги добавлены к задаче: важное"
```

---

## Итог

**Архитектура построена по принципу:**
1. **Пользователь → Обработка → GPT → Маршрутизация → Сервис → API → Ответ**

**Ключевые решения:**
- GPT определяет действие и параметры
- Command Router направляет в нужный сервис
- Каждый сервис знает свой API endpoint
- Кэш решает проблему поиска задач по названию
- Четкое разделение ответственности между компонентами

---

**Дата создания:** 2024-11-04  
**Автор:** System Architect

