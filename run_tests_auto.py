#!/usr/bin/env python3
"""
Автоматический запуск всех тестов по порядку
"""
import asyncio
import sys
from pathlib import Path

project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Импортируем тесты из test_integration_with_mocks.py
from tests.test_integration_with_mocks import (
    TestIntegrationWithMocks,
    ticktick_client,
    test_context
)
from src.api.ticktick_client import TickTickClient


async def run_all_tests():
    """Запускаем все тесты по порядку"""
    print("\n" + "="*70)
    print("АВТОМАТИЧЕСКОЕ ТЕСТИРОВАНИЕ ВСЕХ ФУНКЦИЙ")
    print("="*70)
    
    # Инициализируем клиент и контекст
    client = TickTickClient()
    await client.authenticate()
    
    context = {
        "test_results": {},
        "created_task_ids": [],
        "test_project_id": None,
    }
    
    projects = await client.get_projects()
    if projects:
        context["test_project_id"] = projects[0].get("id")
    
    # Создаем экземпляр тестового класса
    test_instance = TestIntegrationWithMocks()
    
    # Список тестов в порядке выполнения
    tests = [
        ("1. Создание задач", test_instance.test_1_create_task_api),
        ("2. Редактирование задач", test_instance.test_2_update_task_api),
        ("3. Удаление задач", test_instance.test_3_delete_task_api),
        ("4. Перенос задач", test_instance.test_4_move_task_api),
        ("5. Массовый перенос", test_instance.test_5_bulk_move_overdue_api),
        ("6. Управление тегами", test_instance.test_6_manage_tags_api),
        ("7. Управление заметками", test_instance.test_7_manage_notes_api),
        ("8. Повторяющиеся задачи", test_instance.test_8_recurring_tasks_api),
        ("9. Напоминания", test_instance.test_9_reminders_api),
    ]
    
    for test_name, test_func in tests:
        print(f"\n{'='*70}")
        print(f"Запуск: {test_name}")
        print(f"{'='*70}")
        
        try:
            # Передаем фикстуры как параметры
            await test_func(client, context)
            print(f"✅ {test_name} - завершен")
        except Exception as e:
            print(f"❌ {test_name} - ошибка: {e}")
            import traceback
            traceback.print_exc()
    
    # Генерируем отчет
    try:
        await test_instance.test_final_report_api(context)
    except Exception as e:
        print(f"⚠️ Ошибка при генерации отчета: {e}")
    
    print("\n" + "="*70)
    print("ТЕСТИРОВАНИЕ ЗАВЕРШЕНО")
    print("="*70)


if __name__ == "__main__":
    asyncio.run(run_all_tests())

