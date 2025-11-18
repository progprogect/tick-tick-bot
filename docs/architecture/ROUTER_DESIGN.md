# Проектирование умного роутера
## Telegram Bot для управления TickTick

**Дата:** 2024-11-04  
**Версия:** 1.0  
**Статус:** Проектирование

---

## Проблема текущей архитектуры

### Текущие ограничения:

1. **Жесткий if-elif роутер** - негибкий, сложно добавлять новые операции
2. **Одно действие за раз** - GPT определяет только один `action`, но пользователь может хотеть сделать несколько вещей
3. **Нет контекста операций** - не понимаем "заменить" vs "добавить" vs "объединить"
4. **Нет метаданных операций** - как обрабатывать каждое поле (merge, replace, append и т.д.)
5. **Дублирование логики** - каждый сервис сам ищет задачу, обновляет кэш и т.д.

### Примеры проблемных сценариев:

**Сценарий 1:** "Измени задачу X, замени теги на [важное, срочно], добавь заметку 'не забыть'"
- Сейчас: GPT определит `update_task`, но теги будут объединены, а не заменены
- Нужно: понимать "заменить теги" vs "добавить теги"

**Сценарий 2:** "Измени задачу X на завтра и в список Работа"
- Сейчас: работает, но логика размазана
- Нужно: четкое разделение операций

**Сценарий 3:** "Добавь тег важное к задаче X и перенеси на завтра"
- Сейчас: GPT может определить `add_tags` (только тег) или `update_task` (оба параметра)
- Нужно: композитная команда с несколькими операциями

---

## Варианты архитектурных решений

### Вариант 1: Операционная модель с метаданными (Operation Model)

**Идея:** GPT возвращает не просто `action`, а массив операций с метаданными о том, как обрабатывать каждое поле.

**Структура:**
```python
class OperationType(str, Enum):
    REPLACE = "replace"  # Заменить значение
    MERGE = "merge"      # Объединить с существующим
    APPEND = "append"    # Добавить к существующему
    REMOVE = "remove"    # Удалить из существующего

class FieldOperation(BaseModel):
    field: str  # "tags", "notes", "dueDate", "title", etc.
    operation: OperationType
    value: Any
    
class ParsedCommand(BaseModel):
    actions: List[ActionType]  # Может быть несколько действий
    task_identifier: TaskIdentifier  # Как найти задачу
    field_operations: List[FieldOperation]  # Операции над полями
    metadata: Dict[str, Any]  # Дополнительные метаданные
```

**Пример:**
```json
{
  "actions": ["update_task"],
  "task_identifier": {
    "type": "title",
    "value": "купить молоко"
  },
  "field_operations": [
    {"field": "dueDate", "operation": "replace", "value": "2024-11-05"},
    {"field": "tags", "operation": "replace", "value": ["важное", "срочно"]},
    {"field": "notes", "operation": "append", "value": "не забыть"}
  ]
}
```

**Преимущества:**
- ✅ Гибкость - GPT сам определяет контекст операций
- ✅ Композитные команды - несколько операций одновременно
- ✅ Явный контекст - понятно replace vs merge
- ✅ Расширяемость - легко добавить новые типы операций

**Недостатки:**
- ⚠️ Сложнее для GPT - нужно больше контекста в промпте
- ⚠️ Более сложная структура данных

---

### Вариант 2: Стратегический паттерн с регистрацией операций (Strategy Pattern)

**Идея:** Каждая операция - это стратегия, которая регистрируется и может обрабатывать метаданные.

**Структура:**
```python
class OperationStrategy(ABC):
    @abstractmethod
    async def execute(self, command: ParsedCommand, context: OperationContext) -> str:
        pass
    
    @abstractmethod
    def can_handle(self, field: str, operation_type: str) -> bool:
        pass

class ReplaceTagsStrategy(OperationStrategy):
    def can_handle(self, field: str, operation_type: str) -> bool:
        return field == "tags" and operation_type == "replace"
    
    async def execute(self, command, context):
        # Заменить теги полностью
        pass

class MergeTagsStrategy(OperationStrategy):
    def can_handle(self, field: str, operation_type: str) -> bool:
        return field == "tags" and operation_type == "merge"
    
    async def execute(self, command, context):
        # Объединить теги с существующими
        pass

class OperationRouter:
    def __init__(self):
        self.strategies: List[OperationStrategy] = []
    
    def register_strategy(self, strategy: OperationStrategy):
        self.strategies.append(strategy)
    
    async def route(self, command: ParsedCommand) -> str:
        # Найти подходящие стратегии для каждой операции
        for operation in command.field_operations:
            strategy = self.find_strategy(operation)
            await strategy.execute(command, context)
```

**Преимущества:**
- ✅ Расширяемость - легко добавить новые стратегии
- ✅ Тестируемость - каждая стратегия тестируется отдельно
- ✅ Соответствие SOLID - Open/Closed Principle

**Недостатки:**
- ⚠️ Больше кода - нужно создать стратегии для каждой комбинации
- ⚠️ Может быть избыточно для простых случаев

---

### Вариант 3: Контекстные операции с автоматическим определением (Context-Aware Operations)

**Идея:** GPT определяет контекст операций (replace/merge/append) через специальные поля в JSON.

**Структура:**
```python
class ParsedCommand(BaseModel):
    action: ActionType
    task_identifier: TaskIdentifier
    
    # Поля с метаданными операций
    fields: Dict[str, FieldOperation] = {}
    # Пример:
    # {
    #   "tags": {"value": ["важное"], "operation": "replace"},
    #   "notes": {"value": "не забыть", "operation": "append"},
    #   "dueDate": {"value": "2024-11-05", "operation": "replace"}
    # }

class FieldOperation(BaseModel):
    value: Any
    operation: Optional[str] = "replace"  # "replace", "merge", "append", "remove"
```

**Промпт для GPT:**
```
Если пользователь говорит "замени теги на ..." → operation: "replace"
Если пользователь говорит "добавь тег ..." → operation: "merge"
Если пользователь говорит "добавь заметку ..." → operation: "append"
Если пользователь говорит "удали тег ..." → operation: "remove"
```

**Роутер:**
```python
async def route(self, command: ParsedCommand) -> str:
    # Определить основной сервис по action
    service = self.get_service_for_action(command.action)
    
    # Для каждого поля применить операцию
    for field_name, field_op in command.fields.items():
        if field_op.operation == "merge":
            # Объединить с существующим
        elif field_op.operation == "replace":
            # Заменить полностью
        # и т.д.
```

**Преимущества:**
- ✅ Проще для GPT - понятная структура
- ✅ Гибкость - разные операции для разных полей
- ✅ Явный контекст в данных

**Недостатки:**
- ⚠️ Роутер должен знать логику обработки каждого типа операции

---

### Вариант 4: Композитные команды с последовательным выполнением (Composite Commands)

**Идея:** GPT может возвращать массив операций, которые выполняются последовательно.

**Структура:**
```python
class ParsedCommand(BaseModel):
    operations: List[Operation]  # Массив операций
    
class Operation(BaseModel):
    type: ActionType
    params: Dict[str, Any]
    context: Optional[Dict[str, str]] = {}  # Метаданные: "replace", "merge", etc.
```

**Пример:**
```json
{
  "operations": [
    {
      "type": "update_task",
      "params": {"title": "купить молоко", "dueDate": "2024-11-05"},
      "context": {"dueDate": "replace"}
    },
    {
      "type": "update_task",
      "params": {"title": "купить молоко", "tags": ["важное"]},
      "context": {"tags": "replace"}
    },
    {
      "type": "update_task",
      "params": {"title": "купить молоко", "notes": "не забыть"},
      "context": {"notes": "append"}
    }
  ]
}
```

**Роутер:**
```python
async def route(self, command: ParsedCommand) -> str:
    results = []
    for operation in command.operations:
        service = self.get_service(operation.type)
        result = await service.execute(operation.params, operation.context)
        results.append(result)
    return self.combine_results(results)
```

**Преимущества:**
- ✅ Простота - каждая операция независима
- ✅ Гибкость - можно комбинировать любые операции
- ✅ Понятность - явная последовательность

**Недостатки:**
- ⚠️ Множественные API-запросы - неэффективно
- ⚠️ Нет атомарности - если одна операция упала, остальные уже выполнены

---

### Вариант 5: Универсальный TaskModifier с контекстными операциями (Рекомендуемый)

**Идея:** Комбинированный подход - универсальный модификатор задач с контекстными операциями.

**Структура:**
```python
class FieldModifier(str, Enum):
    REPLACE = "replace"  # Заменить значение
    MERGE = "merge"     # Объединить (для тегов, заметок)
    APPEND = "append"   # Добавить к концу (для заметок)
    REMOVE = "remove"   # Удалить (для тегов)

class ParsedCommand(BaseModel):
    action: ActionType
    task_identifier: TaskIdentifier
    
    # Поля с контекстом операций
    modifications: Dict[str, FieldModification] = {}
    
class FieldModification(BaseModel):
    value: Any
    modifier: FieldModifier = FieldModifier.REPLACE  # По умолчанию replace
    
class TaskModifier:
    """Универсальный модификатор задач"""
    
    async def modify_task(
        self,
        task_id: str,
        modifications: Dict[str, FieldModification],
        context: OperationContext
    ) -> str:
        # Получить текущее состояние задачи
        current_data = await self.get_task_data(task_id)
        
        # Применить каждую модификацию
        update_data = {}
        for field_name, modification in modifications.items():
            if modification.modifier == FieldModifier.REPLACE:
                update_data[field_name] = modification.value
            elif modification.modifier == FieldModifier.MERGE:
                current_value = current_data.get(field_name)
                update_data[field_name] = self.merge(current_value, modification.value)
            elif modification.modifier == FieldModifier.APPEND:
                current_value = current_data.get(field_name)
                update_data[field_name] = self.append(current_value, modification.value)
            # и т.д.
        
        # Один запрос к API со всеми изменениями
        return await self.client.update_task(task_id, **update_data)
```

**Промпт для GPT:**
```
Определи контекст операций для каждого поля:
- "замени теги" → {"tags": {"value": [...], "modifier": "replace"}}
- "добавь тег" → {"tags": {"value": [...], "modifier": "merge"}}
- "добавь заметку" → {"notes": {"value": "...", "modifier": "append"}}
- "измени дату" → {"dueDate": {"value": "...", "modifier": "replace"}}
```

**Роутер:**
```python
async def route(self, command: ParsedCommand) -> str:
    if command.action == ActionType.UPDATE_TASK:
        # Универсальный модификатор для всех операций с задачей
        return await self.task_modifier.modify_task(
            task_id=command.task_identifier.id,
            modifications=command.modifications,
            context=command.context
        )
    elif command.action == ActionType.CREATE_TASK:
        # Специфичная логика создания
        return await self.task_manager.create_task(command)
    # и т.д.
```

**Преимущества:**
- ✅ Универсальность - один метод обрабатывает все модификации
- ✅ Один API-запрос - эффективно
- ✅ Атомарность - все изменения применяются вместе
- ✅ Гибкость - GPT определяет контекст операций
- ✅ Расширяемость - легко добавить новые модификаторы

**Недостатки:**
- ⚠️ Нужно четко определить логику для каждого типа поля и модификатора

---

## Рекомендуемое решение: Вариант 5 + Улучшения

### Архитектура:

```
┌─────────────────┐
│   GPT Service   │ → ParsedCommand с modifications
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Smart Router   │ → Определяет стратегию обработки
└────────┬────────┘
         │
         ├─→ CREATE_TASK → TaskManager.create_task()
         ├─→ UPDATE_TASK → TaskModifier.modify_task() (универсальный)
         ├─→ DELETE_TASK → TaskManager.delete_task()
         └─→ ... другие действия
```

### Структура данных:

```python
class TaskIdentifier(BaseModel):
    """Как найти задачу"""
    type: str  # "title", "id", "context"
    value: str

class FieldModification(BaseModel):
    """Модификация поля с контекстом"""
    value: Any
    modifier: FieldModifier = FieldModifier.REPLACE
    # Опционально: метаданные для сложных случаев
    metadata: Dict[str, Any] = {}

class ParsedCommand(BaseModel):
    """Улучшенная команда с контекстными операциями"""
    action: ActionType
    task_identifier: Optional[TaskIdentifier] = None
    
    # Универсальные модификации (для update_task)
    modifications: Dict[str, FieldModification] = {}
    
    # Специфичные параметры для других действий
    # (для обратной совместимости)
    title: Optional[str] = None
    due_date: Optional[str] = None
    tags: Optional[List[str]] = None
    notes: Optional[str] = None
    # ...
```

### Примеры команд:

**Команда 1:** "Измени задачу купить молоко на завтра"
```json
{
  "action": "update_task",
  "task_identifier": {"type": "title", "value": "купить молоко"},
  "modifications": {
    "dueDate": {"value": "2024-11-05", "modifier": "replace"}
  }
}
```

**Команда 2:** "Замени теги задачи купить молоко на [важное, срочно]"
```json
{
  "action": "update_task",
  "task_identifier": {"type": "title", "value": "купить молоко"},
  "modifications": {
    "tags": {"value": ["важное", "срочно"], "modifier": "replace"}
  }
}
```

**Команда 3:** "Добавь тег важное к задаче купить молоко"
```json
{
  "action": "update_task",
  "task_identifier": {"type": "title", "value": "купить молоко"},
  "modifications": {
    "tags": {"value": ["важное"], "modifier": "merge"}
  }
}
```

**Команда 4:** "Измени задачу купить молоко: замени теги на [важное], перенеси на завтра, добавь заметку 'не забыть'"
```json
{
  "action": "update_task",
  "task_identifier": {"type": "title", "value": "купить молоко"},
  "modifications": {
    "tags": {"value": ["важное"], "modifier": "replace"},
    "dueDate": {"value": "2024-11-05", "modifier": "replace"},
    "notes": {"value": "не забыть", "modifier": "append"}
  }
}
```

---

## Преимущества рекомендуемого решения

1. **Гибкость:** GPT определяет контекст операций (replace vs merge)
2. **Универсальность:** Один `TaskModifier` обрабатывает все модификации
3. **Эффективность:** Один API-запрос для всех изменений
4. **Атомарность:** Все изменения применяются вместе
5. **Расширяемость:** Легко добавить новые модификаторы
6. **Понятность:** Явный контекст в структуре данных

---

## Детали реализации

### 1. TaskModifier - универсальный модификатор

```python
class TaskModifier:
    """Универсальный модификатор задач с контекстными операциями"""
    
    def __init__(self, ticktick_client, cache):
        self.client = ticktick_client
        self.cache = cache
    
    async def modify_task(
        self,
        task_id: str,
        modifications: Dict[str, FieldModification]
    ) -> str:
        # 1. Получить текущее состояние из кэша
        current_data = self.cache.get_task_data(task_id)
        
        # 2. Применить каждую модификацию
        update_data = {}
        for field_name, modification in modifications.items():
            processed_value = self._apply_modification(
                field_name,
                modification,
                current_data
            )
            update_data[field_name] = processed_value
        
        # 3. Один запрос к API
        await self.client.update_task(task_id, **update_data)
        
        # 4. Обновить кэш
        self._update_cache(task_id, update_data)
        
        return format_modifications(modifications)
    
    def _apply_modification(
        self,
        field_name: str,
        modification: FieldModification,
        current_data: Dict
    ) -> Any:
        """Применить модификацию к полю"""
        
        if modification.modifier == FieldModifier.REPLACE:
            return modification.value
        
        elif modification.modifier == FieldModifier.MERGE:
            current_value = current_data.get(field_name, [])
            if field_name == "tags":
                return list(set(current_value + modification.value))
            # Для других полей - объединение
            return current_value + modification.value
        
        elif modification.modifier == FieldModifier.APPEND:
            current_value = current_data.get(field_name, "")
            if field_name == "notes":
                return f"{current_value}\n\n{modification.value}" if current_value else modification.value
            return current_value + modification.value
        
        elif modification.modifier == FieldModifier.REMOVE:
            current_value = current_data.get(field_name, [])
            if field_name == "tags":
                return [tag for tag in current_value if tag not in modification.value]
            # Для других полей - удаление
            return None
        
        return modification.value
```

### 2. Умный роутер

```python
class SmartRouter:
    """Умный роутер с динамической маршрутизацией"""
    
    def __init__(self):
        self.task_manager = TaskManager(...)
        self.task_modifier = TaskModifier(...)
        self.tag_manager = TagManager(...)
        # ... другие сервисы
    
    async def route(self, command: ParsedCommand) -> str:
        """Маршрутизация с умной обработкой"""
        
        # 1. Найти задачу если нужно
        if command.task_identifier and not command.task_id:
            task_id = await self._resolve_task_identifier(command.task_identifier)
            command.task_id = task_id
        
        # 2. Маршрутизация по action
        if command.action == ActionType.UPDATE_TASK:
            # Если есть modifications - использовать TaskModifier
            if command.modifications:
                return await self.task_modifier.modify_task(
                    task_id=command.task_id,
                    modifications=command.modifications
                )
            # Иначе - стандартный update_task (для обратной совместимости)
            else:
                return await self.task_manager.update_task(command)
        
        elif command.action == ActionType.CREATE_TASK:
            return await self.task_manager.create_task(command)
        
        # ... другие действия
```

### 3. Улучшенный промпт для GPT

```
Определи контекст операций для каждого поля:

Правила для тегов:
- "замени теги" → modifier: "replace"
- "добавь тег" → modifier: "merge"
- "удали тег" → modifier: "remove"

Правила для заметок:
- "замени заметку" → modifier: "replace"
- "добавь заметку" → modifier: "append"
- "добавь к заметке" → modifier: "append"

Правила для других полей:
- "измени дату" → modifier: "replace"
- "измени приоритет" → modifier: "replace"

Верни JSON:
{
  "action": "update_task",
  "task_identifier": {"type": "title", "value": "..."},
  "modifications": {
    "field_name": {
      "value": ...,
      "modifier": "replace|merge|append|remove"
    }
  }
}
```

---

## Сравнение вариантов

| Критерий | Вариант 1 | Вариант 2 | Вариант 3 | Вариант 4 | Вариант 5 |
|----------|-----------|-----------|-----------|-----------|-----------|
| Гибкость | ✅✅✅ | ✅✅ | ✅✅ | ✅✅ | ✅✅✅ |
| Простота для GPT | ⚠️⚠️ | ✅✅ | ✅✅✅ | ✅✅ | ✅✅✅ |
| Эффективность | ✅✅✅ | ✅✅ | ✅✅✅ | ⚠️ | ✅✅✅ |
| Расширяемость | ✅✅ | ✅✅✅ | ✅ | ✅✅ | ✅✅✅ |
| Атомарность | ✅✅✅ | ✅✅✅ | ✅✅✅ | ⚠️ | ✅✅✅ |
| Сложность реализации | ⚠️⚠️ | ⚠️⚠️⚠️ | ✅ | ✅ | ⚠️ |

---

## Рекомендация

**Выбрать: Вариант 5 (Универсальный TaskModifier с контекстными операциями)**

**Причины:**
1. Баланс между гибкостью и простотой
2. GPT легко определяет контекст операций
3. Один API-запрос для всех изменений
4. Легко расширять новыми модификаторами
5. Явный контекст в структуре данных

**План внедрения:**
1. Создать `TaskModifier` класс
2. Расширить `ParsedCommand` с `modifications`
3. Обновить промпт GPT для определения контекста
4. Обновить роутер для использования `TaskModifier`
5. Сохранить обратную совместимость со старым форматом

---

**Дата создания:** 2024-11-04  
**Статус:** Проектирование завершено, ожидает одобрения

