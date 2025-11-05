# Telegram Bot для управления TickTick

Telegram-бот для управления задачами в TickTick через естественный язык с использованием AI (OpenAI GPT).

## Возможности

- ✅ Создание задач через текст или голос
- ✅ Редактирование и удаление задач
- ✅ Перенос задач между списками
- ✅ Массовые операции (перенос просроченных задач)
- ✅ Управление тегами и заметками
- ✅ Повторяющиеся задачи и напоминания
- ✅ Аналитика рабочего времени
- ✅ Оптимизация расписания через AI

## Установка

### Требования

- Python 3.11+
- Telegram Bot Token
- OpenAI API Key
- TickTick аккаунт

### Шаги установки

1. Клонируйте репозиторий:
```bash
git clone <repository-url>
cd tick-tick
```

2. Создайте виртуальное окружение:
```bash
python -m venv venv
source venv/bin/activate  # Для Windows: venv\Scripts\activate
```

3. Установите зависимости:
```bash
pip install -r requirements.txt
```

4. Создайте файл `.env` на основе `.env.example`:
```bash
cp .env.example .env
```

5. Заполните `.env` файл с вашими credentials (см. `docs/credentials.md`)

6. Для TickTick API:
   - Зарегистрируйтесь на [TickTick Developer Portal](https://developer.ticktick.com/)
   - Создайте приложение и получите `client_id` и `client_secret`
   - Добавьте их в `.env` файл

## Запуск

### Запуск бота

```bash
python -m src.main
```

### Запуск веб-интерфейса для тестирования

```bash
python -m src.web.main
```

Веб-интерфейс будет доступен по адресу: `http://localhost:8000`

## Использование

1. Найдите бота в Telegram: `@TickTick_My_bot`
2. Отправьте команду `/start` для начала работы
3. Отправляйте команды текстом или голосом:
   - "Создай задачу купить молоко"
   - "Перенеси все просроченные задачи со вчера на сегодня"
   - "Добавь тег срочно к задаче подготовить отчет"

## Структура проекта

```
tick-tick/
├── src/                    # Исходный код
│   ├── api/               # API клиенты
│   ├── services/          # Бизнес-логика
│   ├── models/            # Модели данных
│   ├── utils/             # Утилиты
│   └── web/               # Веб-интерфейс
├── docs/                   # Документация
├── tests/                  # Тесты
└── requirements.txt        # Зависимости
```

## Документация

Полная документация находится в папке `docs/`:
- `docs/README.md` - Навигация по документации
- `docs/requirements/BRD.md` - Бизнес-требования
- `docs/credentials.md` - Ключи и доступы

## Разработка

### Запуск тестов

```bash
pytest tests/
```

### Форматирование кода

```bash
black src/
flake8 src/
```

## Лицензия

MIT

## Автор

System Architect


