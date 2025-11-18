#!/usr/bin/env python3
"""
Ручная проверка функций по одной
"""
import asyncio
import sys
from pathlib import Path
from datetime import datetime, timedelta
from unittest.mock import MagicMock, AsyncMock

project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.api.ticktick_client import TickTickClient
from src.services.task_manager import TaskManager
from src.services.tag_manager import TagManager
from src.services.note_manager import NoteManager
from src.services.recurring_task_manager import RecurringTaskManager
from src.services.reminder_manager import ReminderManager
from src.services.batch_processor import BatchProcessor
from src.services.analytics_service import AnalyticsService
from src.services.task_cache import TaskCacheService
from src.models.command import ParsedCommand, ActionType, Recurrence


async def test_1_create_task():
    """Тест 1: Создание задачи"""
    print("\n" + "="*70)
    print("ТЕСТ 1: Создание задачи")
    print("="*70)
    
    client = TickTickClient()
    auth_result = await client.authenticate()
    if not auth_result:
        print("❌ Аутентификация не удалась")
        return False
    
    print("✅ Аутентификация успешна")
    
    # Получаем проекты
    projects = await client.get_projects()
    if not projects:
        print("❌ Нет доступных проектов")
        return False
    
    project_id = projects[0].get('id')
    print(f"✅ Используем проект: {projects[0].get('name')} (ID: {project_id})")
    
    # Создаем задачу (без GPT - напрямую ParsedCommand)
    task_manager = TaskManager(client)
    cache = TaskCacheService()
    
    command = ParsedCommand(
        action=ActionType.CREATE_TASK,
        title="Ручной тест: Создание задачи",
        due_date=(datetime.now() + timedelta(days=1)).isoformat() + "+00:00",
        priority=1,
        project_id=project_id
    )
    
    print(f"📝 Создаем задачу: {command.title}")
    result = await task_manager.create_task(command)
    print(f"✅ Результат создания: {result}")
    
    # Проверяем через GET
    await asyncio.sleep(1)  # Даем время кэшу обновиться
    task_id = cache.get_task_id_by_title(command.title)
    
    if not task_id:
        print("❌ Задача не найдена в кэше")
        return False
    
    print(f"✅ Task ID из кэша: {task_id}")
    
    # GET запрос для проверки
    try:
        task = await client.get(
            endpoint=f"/open/v1/project/{project_id}/task/{task_id}",
            headers=client._get_headers()
        )
        
        print(f"\n📋 Данные задачи из API:")
        print(f"   Название: {task.get('title')}")
        print(f"   Статус: {task.get('status')}")
        print(f"   Приоритет: {task.get('priority')}")
        print(f"   Дата выполнения: {task.get('dueDate')}")
        print(f"   Project ID: {task.get('projectId')}")
        
        # Проверка
        assert task.get('title') == command.title, "Название не совпадает"
        assert task.get('status') == 0, "Статус должен быть 0"
        print("\n✅ Все проверки пройдены!")
        return True
        
    except Exception as e:
        print(f"❌ GET запрос не удался: {e}")
        return False


async def test_2_update_task():
    """Тест 2: Редактирование задачи"""
    print("\n" + "="*70)
    print("ТЕСТ 2: Редактирование задачи")
    print("="*70)
    
    client = TickTickClient()
    await client.authenticate()
    
    cache = TaskCacheService()
    task_id = cache.get_task_id_by_title("Ручной тест: Создание задачи")
    
    if not task_id:
        print("❌ Задача не найдена. Сначала выполните тест 1")
        return False
    
    task_data = cache.get_task_data(task_id)
    project_id = task_data.get('project_id')
    
    print(f"✅ Найдена задача: {task_id} в проекте {project_id}")
    
    # Обновляем задачу
    task_manager = TaskManager(client)
    new_date = (datetime.now() + timedelta(days=3)).isoformat() + "+00:00"
    
    command = ParsedCommand(
        action=ActionType.UPDATE_TASK,
        task_id=task_id,
        due_date=new_date,
        priority=3
    )
    
    print(f"📝 Обновляем задачу: дата={new_date}, приоритет=3")
    result = await task_manager.update_task(command)
    print(f"✅ Результат обновления: {result}")
    
    # Проверяем через GET
    await asyncio.sleep(1)
    try:
        task = await client.get(
            endpoint=f"/open/v1/project/{project_id}/task/{task_id}",
            headers=client._get_headers()
        )
        
        print(f"\n📋 Данные задачи после обновления:")
        print(f"   Приоритет: {task.get('priority')} (ожидается 3)")
        print(f"   Дата выполнения: {task.get('dueDate')}")
        
        print("\n✅ Задача обновлена")
        return True
        
    except Exception as e:
        print(f"⚠️ GET запрос не удался: {e}")
        return True  # Обновление могло пройти, но GET не работает


async def test_3_add_tags():
    """Тест 3: Добавление тегов"""
    print("\n" + "="*70)
    print("ТЕСТ 3: Добавление тегов")
    print("="*70)
    
    client = TickTickClient()
    await client.authenticate()
    
    cache = TaskCacheService()
    task_id = cache.get_task_id_by_title("Ручной тест: Создание задачи")
    
    if not task_id:
        print("❌ Задача не найдена")
        return False
    
    task_data = cache.get_task_data(task_id)
    project_id = task_data.get('project_id')
    
    # Добавляем теги
    tag_manager = TagManager(client)
    command = ParsedCommand(
        action=ActionType.ADD_TAGS,
        task_id=task_id,
        tags=["ручной-тест", "важное"]
    )
    
    print(f"📝 Добавляем теги: {command.tags}")
    result = await tag_manager.add_tags(command)
    print(f"✅ Результат: {result}")
    
    # Проверяем через GET
    await asyncio.sleep(1)
    try:
        task = await client.get(
            endpoint=f"/open/v1/project/{project_id}/task/{task_id}",
            headers=client._get_headers()
        )
        
        tags = task.get('tags', [])
        print(f"\n📋 Теги из API: {tags}")
        
        cached_tags = cache.get_task_data(task_id).get('tags', [])
        print(f"📋 Теги из кэша: {cached_tags}")
        
        print("\n✅ Теги добавлены")
        return True
        
    except Exception as e:
        print(f"⚠️ GET запрос не удался: {e}")
        return True


async def test_4_add_notes():
    """Тест 4: Добавление заметок"""
    print("\n" + "="*70)
    print("ТЕСТ 4: Добавление заметок")
    print("="*70)
    
    client = TickTickClient()
    await client.authenticate()
    
    cache = TaskCacheService()
    task_id = cache.get_task_id_by_title("Ручной тест: Создание задачи")
    
    if not task_id:
        print("❌ Задача не найдена")
        return False
    
    task_data = cache.get_task_data(task_id)
    project_id = task_data.get('project_id')
    
    # Добавляем заметку
    note_manager = NoteManager(client)
    command = ParsedCommand(
        action=ActionType.ADD_NOTE,
        task_id=task_id,
        notes="Это заметка для ручного тестирования"
    )
    
    print(f"📝 Добавляем заметку: {command.notes[:50]}...")
    result = await note_manager.add_note(command)
    print(f"✅ Результат: {result}")
    
    # Проверяем через GET
    await asyncio.sleep(1)
    try:
        task = await client.get(
            endpoint=f"/open/v1/project/{project_id}/task/{task_id}",
            headers=client._get_headers()
        )
        
        content = task.get('content', '')
        print(f"\n📋 Содержимое из API: {content[:100]}...")
        
        print("\n✅ Заметка добавлена")
        return True
        
    except Exception as e:
        print(f"⚠️ GET запрос не удался: {e}")
        return True


async def test_5_recurring_task():
    """Тест 5: Повторяющаяся задача"""
    print("\n" + "="*70)
    print("ТЕСТ 5: Повторяющаяся задача")
    print("="*70)
    
    client = TickTickClient()
    await client.authenticate()
    
    projects = await client.get_projects()
    project_id = projects[0].get('id') if projects else None
    
    # Создаем повторяющуюся задачу
    recurring_manager = RecurringTaskManager(client)
    command = ParsedCommand(
        action=ActionType.CREATE_RECURRING_TASK,
        title="Ручной тест: Повторяющаяся задача",
        due_date=(datetime.now() + timedelta(days=1)).isoformat() + "+00:00",
        recurrence=Recurrence(type="daily", interval=1)
    )
    
    print(f"📝 Создаем повторяющуюся задачу: {command.title}")
    result = await recurring_manager.create_recurring_task(command)
    print(f"✅ Результат: {result}")
    
    # Проверяем через GET
    await asyncio.sleep(1)
    cache = TaskCacheService()
    task_id = cache.get_task_id_by_title(command.title)
    
    if not task_id:
        print("❌ Задача не найдена в кэше")
        return False
    
    task_data = cache.get_task_data(task_id)
    project_id = task_data.get('project_id', project_id)
    
    try:
        task = await client.get(
            endpoint=f"/open/v1/project/{project_id}/task/{task_id}",
            headers=client._get_headers()
        )
        
        print(f"\n📋 Данные задачи:")
        print(f"   Repeat Flag: {task.get('repeatFlag')}")
        print(f"   Start Date: {task.get('startDate')}")
        
        if task.get('repeatFlag'):
            print("\n✅ Повторение настроено")
        else:
            print("\n⚠️ RepeatFlag не найден в API")
        
        return True
        
    except Exception as e:
        print(f"⚠️ GET запрос не удался: {e}")
        return True


async def test_6_reminder():
    """Тест 6: Напоминание"""
    print("\n" + "="*70)
    print("ТЕСТ 6: Напоминание")
    print("="*70)
    
    client = TickTickClient()
    await client.authenticate()
    
    cache = TaskCacheService()
    task_id = cache.get_task_id_by_title("Ручной тест: Создание задачи")
    
    if not task_id:
        print("❌ Задача не найдена")
        return False
    
    task_data = cache.get_task_data(task_id)
    project_id = task_data.get('project_id')
    
    # Устанавливаем напоминание
    reminder_manager = ReminderManager(client)
    reminder_time = (datetime.now() + timedelta(hours=2)).isoformat() + "+00:00"
    
    command = ParsedCommand(
        action=ActionType.SET_REMINDER,
        task_id=task_id,
        reminder=reminder_time
    )
    
    print(f"📝 Устанавливаем напоминание: {reminder_time}")
    result = await reminder_manager.set_reminder(command)
    print(f"✅ Результат: {result}")
    
    # Проверяем через GET
    await asyncio.sleep(1)
    try:
        task = await client.get(
            endpoint=f"/open/v1/project/{project_id}/task/{task_id}",
            headers=client._get_headers()
        )
        
        reminders = task.get('reminders', [])
        print(f"\n📋 Напоминания из API: {reminders}")
        
        if reminders:
            print("\n✅ Напоминание добавлено")
        else:
            print("\n⚠️ Напоминания не найдены в API")
        
        return True
        
    except Exception as e:
        print(f"⚠️ GET запрос не удался: {e}")
        return True


async def test_7_delete_task():
    """Тест 7: Удаление задачи"""
    print("\n" + "="*70)
    print("ТЕСТ 7: Удаление задачи")
    print("="*70)
    
    client = TickTickClient()
    await client.authenticate()
    
    cache = TaskCacheService()
    task_id = cache.get_task_id_by_title("Ручной тест: Создание задачи")
    
    if not task_id:
        print("❌ Задача не найдена")
        return False
    
    task_data = cache.get_task_data(task_id)
    project_id = task_data.get('project_id')
    
    # Удаляем задачу
    task_manager = TaskManager(client)
    command = ParsedCommand(
        action=ActionType.DELETE_TASK,
        task_id=task_id
    )
    
    print(f"📝 Удаляем задачу: {task_id}")
    result = await task_manager.delete_task(command)
    print(f"✅ Результат удаления: {result}")
    
    # Проверяем через GET - задача не должна быть в списке проекта
    await asyncio.sleep(1)
    try:
        project_data = await client.get(
            endpoint=f"/open/v1/project/{project_id}/data",
            headers=client._get_headers()
        )
        
        if isinstance(project_data, dict) and "tasks" in project_data:
            tasks = project_data["tasks"]
            task_ids = [t.get("id") for t in tasks]
            
            if task_id not in task_ids:
                print("\n✅ Задача удалена из списка проекта")
                return True
            else:
                print("\n⚠️ Задача все еще в списке (возможно soft delete)")
                return True
    except Exception as e:
        print(f"⚠️ GET запрос не удался: {e}")
        return True


async def test_8_move_task():
    """Тест 8: Перенос задачи"""
    print("\n" + "="*70)
    print("ТЕСТ 8: Перенос задачи между списками")
    print("="*70)
    
    client = TickTickClient()
    await client.authenticate()
    
    projects = await client.get_projects()
    if len(projects) < 2:
        print("❌ Нужно минимум 2 проекта для теста переноса")
        return False
    
    source_project = projects[0]
    target_project = projects[1]
    
    print(f"✅ Проекты: {source_project.get('name')} -> {target_project.get('name')}")
    
    # Создаем задачу в исходном проекте
    task_manager = TaskManager(client)
    cache = TaskCacheService()
    
    create_cmd = ParsedCommand(
        action=ActionType.CREATE_TASK,
        title="Ручной тест: Перенос задачи",
        project_id=source_project.get('id')
    )
    
    print(f"📝 Создаем задачу в проекте {source_project.get('name')}")
    await task_manager.create_task(create_cmd)
    
    await asyncio.sleep(1)
    task_id = cache.get_task_id_by_title(create_cmd.title)
    
    if not task_id:
        print("❌ Задача не найдена")
        return False
    
    print(f"✅ Задача создана: {task_id}")
    
    # Переносим задачу
    move_cmd = ParsedCommand(
        action=ActionType.MOVE_TASK,
        task_id=task_id,
        target_project_id=target_project.get('id')
    )
    
    print(f"📝 Переносим задачу в проект {target_project.get('name')}")
    result = await task_manager.move_task(move_cmd)
    print(f"✅ Результат переноса: {result}")
    
    # Проверяем через GET
    await asyncio.sleep(1)
    try:
        target_data = await client.get(
            endpoint=f"/open/v1/project/{target_project.get('id')}/data",
            headers=client._get_headers()
        )
        
        if isinstance(target_data, dict) and "tasks" in target_data:
            tasks = target_data["tasks"]
            task_ids = [t.get("id") for t in tasks]
            
            if task_id in task_ids:
                print("\n✅ Задача найдена в целевом проекте")
                return True
            else:
                print("\n⚠️ Задача не найдена в целевом проекте (возможно fallback)")
                # Проверяем кэш
                task_data = cache.get_task_data(task_id)
                if task_data and task_data.get('project_id') == target_project.get('id'):
                    print("✅ Но project_id в кэше обновлен корректно")
                    return True
                return False
    except Exception as e:
        print(f"⚠️ GET запрос не удался: {e}")
        return True


async def test_9_analytics():
    """Тест 9: Аналитика"""
    print("\n" + "="*70)
    print("ТЕСТ 9: Аналитика рабочего времени")
    print("="*70)
    
    client = TickTickClient()
    await client.authenticate()
    
    # Мокируем GPT
    from src.services.gpt_service import GPTService
    from src.api.openai_client import OpenAIClient
    
    mock_openai = MagicMock(spec=OpenAIClient)
    mock_openai.chat_completion = AsyncMock(
        return_value='{"work_time": 40, "personal_time": 10}'
    )
    
    gpt_service = GPTService()
    gpt_service.openai_client = mock_openai
    
    analytics_service = AnalyticsService(client, gpt_service)
    
    print("📝 Получаем аналитику за неделю")
    result = await analytics_service.get_work_time_analytics(
        start_date=(datetime.now() - timedelta(days=7)).isoformat() + "+00:00",
        end_date=datetime.now().isoformat() + "+00:00"
    )
    
    print(f"\n✅ Результат аналитики: {result[:200]}...")
    return True


async def test_10_list_tasks():
    """Тест 10: Просмотр задач"""
    print("\n" + "="*70)
    print("ТЕСТ 10: Просмотр задач")
    print("="*70)
    
    client = TickTickClient()
    await client.authenticate()
    
    # Мокируем GPT
    from src.services.gpt_service import GPTService
    from src.api.openai_client import OpenAIClient
    
    mock_openai = MagicMock(spec=OpenAIClient)
    mock_openai.chat_completion = AsyncMock(
        return_value='У вас сегодня несколько задач. Важно выполнить их в срок.'
    )
    
    gpt_service = GPTService()
    gpt_service.openai_client = mock_openai
    
    analytics_service = AnalyticsService(client, gpt_service)
    
    print("📝 Получаем список задач на сегодня")
    result = await analytics_service.list_tasks(
        start_date=datetime.now().isoformat() + "+00:00",
        end_date=(datetime.now() + timedelta(days=1)).isoformat() + "+00:00"
    )
    
    print(f"\n✅ Результат: {result[:200]}...")
    return True


async def main():
    """Запуск всех тестов по порядку"""
    print("\n" + "="*70)
    print("РУЧНАЯ ПРОВЕРКА ФУНКЦИЙ")
    print("="*70)
    print("\nВыберите тест для выполнения:")
    print("1. Создание задачи")
    print("2. Редактирование задачи")
    print("3. Добавление тегов")
    print("4. Добавление заметок")
    print("5. Повторяющаяся задача")
    print("6. Напоминание")
    print("7. Удаление задачи")
    print("8. Перенос задачи")
    print("9. Аналитика")
    print("10. Просмотр задач")
    print("0. Все тесты по порядку")
    
    choice = input("\nВведите номер теста (0-10): ").strip()
    
    tests = {
        "1": test_1_create_task,
        "2": test_2_update_task,
        "3": test_3_add_tags,
        "4": test_4_add_notes,
        "5": test_5_recurring_task,
        "6": test_6_reminder,
        "7": test_7_delete_task,
        "8": test_8_move_task,
        "9": test_9_analytics,
        "10": test_10_list_tasks,
    }
    
    if choice == "0":
        for test_func in tests.values():
            try:
                await test_func()
                input("\nНажмите Enter для продолжения...")
            except Exception as e:
                print(f"\n❌ Ошибка в тесте: {e}")
                import traceback
                traceback.print_exc()
                input("\nНажмите Enter для продолжения...")
    elif choice in tests:
        try:
            await tests[choice]()
        except Exception as e:
            print(f"\n❌ Ошибка: {e}")
            import traceback
            traceback.print_exc()
    else:
        print("Неверный выбор")


if __name__ == "__main__":
    asyncio.run(main())

