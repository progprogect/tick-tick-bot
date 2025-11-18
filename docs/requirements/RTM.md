# Requirements Traceability Matrix (RTM)
## Telegram Bot для управления TickTick

**Версия:** 1.0  
**Дата:** 2024-11-04  
**Статус:** Draft

---

## Назначение

Requirements Traceability Matrix (RTM) обеспечивает полную трассировку требований от бизнес-целей до реализации, включая:
- Связь между Business Requirements (BR) и Functional Requirements (FR)
- Связь между Functional Requirements (FR) и User Stories (US)
- Связь между User Stories (US) и Acceptance Criteria (AC)
- Связь между Acceptance Criteria (AC) и Use Cases (UC)
- Связь между требованиями и компонентами системы

---

## Легенда

- **BR-XX**: Business Requirement (бизнес-требование)
- **FR-XX**: Functional Requirement (функциональное требование)
- **NFR-XX**: Non-Functional Requirement (нефункциональное требование)
- **US-XX**: User Story (пользовательская история)
- **AC-XX**: Acceptance Criteria (критерий приёмки)
- **UC-XX**: Use Case (сценарий использования)
- **Компонент**: Модуль или компонент системы

---

## Матрица трассировки требований

### 1. Управление задачами

#### FR-1: Создание задач

| Элемент | ID | Связь | Компонент | Статус |
|---------|----|----|-----------|--------|
| BR | BR-1: Управление задачами через естественный язык | → | - | - |
| FR | FR-1: Создание задач | ✓ | TaskManager | Not Started |
| US | US-1: Создание задачи через голос | → | VoiceHandler, GPTService | Not Started |
| US | US-2: Создание задачи через текст | → | TextHandler, GPTService | Not Started |
| AC | AC-1: Создание задачи через голос | → | VoiceHandler, GPTService, TickTickAPI | Not Started |
| AC | AC-2: Создание задачи через текст | → | TextHandler, GPTService, TickTickAPI | Not Started |
| UC | UC-1: Создание задачи через голосовое сообщение | → | VoiceHandler, GPTService, TickTickAPI, n8n | Not Started |
| UC | UC-2: Создание задачи через текстовое сообщение | → | TextHandler, GPTService, TickTickAPI, n8n | Not Started |

**Компоненты:**
- `VoiceHandler`: Обработка голосовых сообщений
- `TextHandler`: Обработка текстовых сообщений
- `GPTService`: Обработка команд через GPT
- `TickTickAPI`: Интеграция с TickTick API
- `n8n`: Workflow orchestration

---

#### FR-2: Редактирование задач

| Элемент | ID | Связь | Компонент | Статус |
|---------|----|----|-----------|--------|
| BR | BR-1: Управление задачами через естественный язык | → | - | - |
| FR | FR-2: Редактирование задач | ✓ | TaskManager | Not Started |
| US | US-3: Редактирование задачи | → | GPTService, TickTickAPI | Not Started |
| AC | AC-3: Редактирование задачи | → | GPTService, TickTickAPI | Not Started |
| UC | UC-6: Редактирование задачи | → | GPTService, TickTickAPI, n8n | Not Started |

**Компоненты:**
- `TaskManager`: Управление задачами
- `GPTService`: Обработка команд через GPT
- `TickTickAPI`: Интеграция с TickTick API
- `n8n`: Workflow orchestration

---

#### FR-3: Удаление задач

| Элемент | ID | Связь | Компонент | Статус |
|---------|----|----|-----------|--------|
| BR | BR-1: Управление задачами через естественный язык | → | - | - |
| FR | FR-3: Удаление задач | ✓ | TaskManager | Not Started |
| US | US-4: Удаление задачи | → | GPTService, TickTickAPI | Not Started |
| AC | AC-4: Удаление задачи | → | GPTService, TickTickAPI | Not Started |

**Компоненты:**
- `TaskManager`: Управление задачами
- `GPTService`: Обработка команд через GPT
- `TickTickAPI`: Интеграция с TickTick API

---

#### FR-4: Перенос задач

| Элемент | ID | Связь | Компонент | Статус |
|---------|----|----|-----------|--------|
| BR | BR-1: Управление задачами через естественный язык | → | - | - |
| FR | FR-4: Перенос задач | ✓ | TaskManager | Not Started |
| US | US-5: Массовый перенос просроченных задач | → | GPTService, TickTickAPI | Not Started |
| US | US-6: Перенос задач между списками | → | GPTService, TickTickAPI | Not Started |
| AC | AC-5: Перенос задач между списками | → | GPTService, TickTickAPI | Not Started |
| AC | AC-6: Массовый перенос просроченных задач | → | GPTService, TickTickAPI | Not Started |
| UC | UC-3: Массовый перенос просроченных задач | → | GPTService, TickTickAPI, n8n | Not Started |

**Компоненты:**
- `TaskManager`: Управление задачами
- `GPTService`: Обработка команд через GPT
- `TickTickAPI`: Интеграция с TickTick API
- `BatchProcessor`: Обработка массовых операций

---

#### FR-5: Управление тегами

| Элемент | ID | Связь | Компонент | Статус |
|---------|----|----|-----------|--------|
| BR | BR-1: Управление задачами через естественный язык | → | - | - |
| FR | FR-5: Управление тегами | ✓ | TagManager | Not Started |
| US | US-7: Добавление тегов к задачам | → | GPTService, TickTickAPI | Not Started |
| US | US-8: Массовое добавление тегов с определением срочности | → | GPTService, TickTickAPI | Not Started |
| AC | AC-7: Добавление тегов к задачам | → | GPTService, TickTickAPI | Not Started |
| AC | AC-8: Массовое добавление тегов с определением срочности | → | GPTService, TickTickAPI | Not Started |
| UC | UC-4: Массовое добавление тегов с определением срочности | → | GPTService, TickTickAPI, n8n | Not Started |

**Компоненты:**
- `TagManager`: Управление тегами
- `GPTService`: Обработка команд через GPT (определение срочности)
- `TickTickAPI`: Интеграция с TickTick API
- `BatchProcessor`: Обработка массовых операций

---

#### FR-6: Управление заметками

| Элемент | ID | Связь | Компонент | Статус |
|---------|----|----|-----------|--------|
| BR | BR-1: Управление задачами через естественный язык | → | - | - |
| FR | FR-6: Управление заметками | ✓ | NoteManager | Not Started |
| US | US-9: Добавление заметок к задачам | → | GPTService, TickTickAPI | Not Started |
| AC | AC-9: Добавление заметок к задачам | → | GPTService, TickTickAPI | Not Started |

**Компоненты:**
- `NoteManager`: Управление заметками
- `GPTService`: Обработка команд через GPT
- `TickTickAPI`: Интеграция с TickTick API

---

#### FR-7: Повторяющиеся задачи

| Элемент | ID | Связь | Компонент | Статус |
|---------|----|----|-----------|--------|
| BR | BR-1: Управление задачами через естественный язык | → | - | - |
| FR | FR-7: Повторяющиеся задачи | ✓ | RecurringTaskManager | Not Started |
| US | US-10: Создание повторяющихся задач | → | GPTService, TickTickAPI | Not Started |
| AC | AC-10: Создание повторяющихся задач | → | GPTService, TickTickAPI | Not Started |
| UC | UC-5: Создание повторяющейся задачи с напоминанием | → | GPTService, TickTickAPI, n8n | Not Started |

**Компоненты:**
- `RecurringTaskManager`: Управление повторяющимися задачами
- `GPTService`: Обработка команд через GPT
- `TickTickAPI`: Интеграция с TickTick API

---

#### FR-8: Напоминания

| Элемент | ID | Связь | Компонент | Статус |
|---------|----|----|-----------|--------|
| BR | BR-1: Управление задачами через естественный язык | → | - | - |
| FR | FR-8: Напоминания | ✓ | ReminderManager | Not Started |
| US | US-11: Установка напоминаний | → | GPTService, TickTickAPI | Not Started |
| AC | AC-11: Установка напоминаний | → | GPTService, TickTickAPI | Not Started |
| UC | UC-5: Создание повторяющейся задачи с напоминанием | → | GPTService, TickTickAPI, n8n | Not Started |

**Компоненты:**
- `ReminderManager`: Управление напоминаниями
- `GPTService`: Обработка команд через GPT
- `TickTickAPI`: Интеграция с TickTick API

---

### 2. Обработка команд

#### FR-10: Распознавание голоса

| Элемент | ID | Связь | Компонент | Статус |
|---------|----|----|-----------|--------|
| BR | BR-2: Голосовое управление | → | - | - |
| FR | FR-10: Распознавание голоса | ✓ | VoiceHandler | Not Started |
| US | US-12: Распознавание голосовых сообщений | → | VoiceHandler, TelegramAPI | Not Started |
| AC | AC-12: Распознавание голосовых сообщений | → | VoiceHandler, TelegramAPI, WhisperAPI | Not Started |
| UC | UC-1: Создание задачи через голосовое сообщение | → | VoiceHandler, TelegramAPI, WhisperAPI | Not Started |

**Компоненты:**
- `VoiceHandler`: Обработка голосовых сообщений
- `TelegramAPI`: Интеграция с Telegram Bot API
- `WhisperAPI`: Конвертация голоса в текст (OpenAI Whisper)

---

#### FR-11: Парсинг команд через GPT

| Элемент | ID | Связь | Компонент | Статус |
|---------|----|----|-----------|--------|
| BR | BR-3: Интеллектуальная обработка команд | → | - | - |
| FR | FR-11: Парсинг команд через GPT | ✓ | GPTService | Not Started |
| US | US-13: Парсинг команд через GPT | → | GPTService, OpenAIAPI | Not Started |
| US | US-14: Контекстное определение срочности | → | GPTService, OpenAIAPI | Not Started |
| AC | AC-13: Парсинг команд через GPT | → | GPTService, OpenAIAPI, n8n | Not Started |
| AC | AC-14: Контекстное определение срочности | → | GPTService, OpenAIAPI | Not Started |
| UC | UC-1, UC-2, UC-3, UC-4, UC-5, UC-6, UC-7, UC-8 | → | GPTService, OpenAIAPI, n8n | Not Started |

**Компоненты:**
- `GPTService`: Обработка команд через GPT
- `OpenAIAPI`: Интеграция с OpenAI API
- `PromptManager`: Управление промптами для GPT
- `n8n`: Workflow orchestration

---

### 3. Аналитика

#### FR-13: Аналитика рабочего времени

| Элемент | ID | Связь | Компонент | Статус |
|---------|----|----|-----------|--------|
| BR | BR-4: Аналитика продуктивности | → | - | - |
| FR | FR-13: Аналитика рабочего времени | ✓ | AnalyticsService | Not Started |
| US | US-15: Аналитика рабочего времени | → | AnalyticsService, TickTickAPI | Not Started |
| AC | AC-15: Аналитика рабочего времени | → | AnalyticsService, TickTickAPI, GPTService | Not Started |
| UC | UC-7: Получение аналитики рабочего времени | → | AnalyticsService, TickTickAPI, GPTService, n8n | Not Started |

**Компоненты:**
- `AnalyticsService`: Сервис аналитики
- `TickTickAPI`: Интеграция с TickTick API
- `GPTService`: Формирование текстовых ответов
- `TimeCalculator`: Подсчет времени

---

#### FR-14: Анализ и оптимизация расписания

| Элемент | ID | Связь | Компонент | Статус |
|---------|----|----|-----------|--------|
| BR | BR-4: Аналитика продуктивности | → | - | - |
| FR | FR-14: Анализ и оптимизация расписания | ✓ | AnalyticsService | Not Started |
| US | US-16: Анализ и оптимизация расписания | → | AnalyticsService, GPTService | Not Started |
| AC | AC-16: Анализ и оптимизация расписания | → | AnalyticsService, GPTService, TickTickAPI | Not Started |
| UC | UC-8: Анализ и оптимизация расписания | → | AnalyticsService, GPTService, TickTickAPI, n8n | Not Started |

**Компоненты:**
- `AnalyticsService`: Сервис аналитики
- `GPTService`: Анализ и формирование рекомендаций
- `TickTickAPI`: Интеграция с TickTick API
- `ScheduleOptimizer`: Оптимизация расписания

---

### 4. Интеграции

#### FR-15: Интеграция с TickTick API

| Элемент | ID | Связь | Компонент | Статус |
|---------|----|----|-----------|--------|
| BR | BR-5: Интеграция с TickTick | → | - | - |
| FR | FR-15: Интеграция с TickTick API | ✓ | TickTickAPI | Not Started |
| US | US-19: Интеграция с TickTick API | → | TickTickAPI | Not Started |
| AC | AC-18: Интеграция с TickTick API | → | TickTickAPI, AuthService | Not Started |
| UC | Все UC, связанные с задачами | → | TickTickAPI | Not Started |

**Компоненты:**
- `TickTickAPI`: Клиент для работы с TickTick OpenAPI
- `AuthService`: Сервис аутентификации OAuth 2.0
- `ErrorHandler`: Обработка ошибок API

---

#### FR-16: Интеграция с Telegram Bot API

| Элемент | ID | Связь | Компонент | Статус |
|---------|----|----|-----------|--------|
| BR | BR-6: Интеграция с Telegram | → | - | - |
| FR | FR-16: Интеграция с Telegram Bot API | ✓ | TelegramAPI | Not Started |
| US | US-18: Интеграция с Telegram Bot API | → | TelegramAPI | Not Started |
| AC | AC-17: Интеграция с Telegram Bot API | → | TelegramAPI | Not Started |
| UC | Все UC | → | TelegramAPI | Not Started |

**Компоненты:**
- `TelegramAPI`: Клиент для работы с Telegram Bot API
- `MessageHandler`: Обработка входящих сообщений
- `ResponseFormatter`: Форматирование ответов

---

#### FR-17: Интеграция через n8n

| Элемент | ID | Связь | Компонент | Статус |
|---------|----|----|-----------|--------|
| BR | BR-7: Workflow orchestration | → | - | - |
| FR | FR-17: Интеграция через n8n | ✓ | n8n | Not Started |
| US | US-20: Интеграция через n8n | → | n8n | Not Started |
| AC | AC-19: Интеграция через n8n | → | n8n | Not Started |
| UC | Все UC | → | n8n | Not Started |

**Компоненты:**
- `n8n`: Workflow orchestration platform
- `WorkflowManager`: Управление workflow в n8n

---

## Матрица зависимостей компонентов

| Компонент | Зависит от | Используется в |
|-----------|------------|----------------|
| `VoiceHandler` | `TelegramAPI`, `WhisperAPI` | UC-1 |
| `TextHandler` | `TelegramAPI` | UC-2, UC-3, UC-4, UC-5, UC-6, UC-7, UC-8 |
| `GPTService` | `OpenAIAPI`, `PromptManager` | Все UC, кроме UC-9 |
| `TickTickAPI` | `AuthService`, `ErrorHandler` | Все UC, связанные с задачами |
| `TaskManager` | `TickTickAPI`, `GPTService` | UC-1, UC-2, UC-3, UC-6 |
| `TagManager` | `TickTickAPI`, `GPTService` | UC-4 |
| `NoteManager` | `TickTickAPI`, `GPTService` | - |
| `RecurringTaskManager` | `TickTickAPI`, `GPTService` | UC-5 |
| `ReminderManager` | `TickTickAPI`, `GPTService` | UC-5 |
| `AnalyticsService` | `TickTickAPI`, `GPTService`, `TimeCalculator` | UC-7, UC-8 |
| `BatchProcessor` | `TickTickAPI` | UC-3, UC-4 |
| `ScheduleOptimizer` | `AnalyticsService`, `GPTService` | UC-8 |
| `TelegramAPI` | - | Все UC |
| `n8n` | `TelegramAPI`, `GPTService`, `TickTickAPI` | Все UC |

---

## Критический путь реализации

```
1. Интеграции (FR-15, FR-16, FR-17)
   ↓
2. Обработка команд (FR-10, FR-11)
   ↓
3. Управление задачами (FR-1, FR-2, FR-3, FR-4)
   ↓
4. Расширенные функции (FR-5, FR-6, FR-7, FR-8)
   ↓
5. Аналитика (FR-13, FR-14)
```

---

## Матрица покрытия требований

### Полнота покрытия

| Категория | FR | US | AC | UC | Покрытие |
|-----------|----|----|----|----|----------|
| Управление задачами | 8 | 11 | 11 | 6 | 100% |
| Обработка команд | 2 | 3 | 3 | - | 100% |
| Аналитика | 2 | 2 | 2 | 2 | 100% |
| Интеграции | 3 | 3 | 3 | - | 100% |
| **Итого** | **15** | **19** | **19** | **8** | **100%** |

---

## История изменений

| Версия | Дата | Автор | Описание изменений |
|--------|------|-------|-------------------|
| 1.0 | 2024-11-04 | System Architect | Первоначальная версия RTM |

