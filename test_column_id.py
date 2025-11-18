"""
Тестовый скрипт для проверки поддержки columnId в TickTick API
Проверяет, можно ли переносить задачи в секции (колонки) через columnId
"""

import asyncio
import json
from src.api.ticktick_client import TickTickClient
from src.config.settings import settings
from src.utils.logger import logger


async def test_column_id_support():
    """Тестирует поддержку columnId в TickTick API"""
    
    print("=" * 80)
    print("ТЕСТ: Поддержка columnId для переноса задач в секции")
    print("=" * 80)
    
    client = TickTickClient()
    
    try:
        # 1. Аутентификация
        print("\n[1/7] Аутентификация...")
        await client.authenticate()
        if not client.access_token:
            print("❌ Ошибка: Не удалось аутентифицироваться")
            return
        print("✅ Аутентификация успешна")
        
        # 2. Получить список проектов
        print("\n[2/7] Получение списка проектов...")
        projects = await client.get_projects()
        if not projects:
            print("❌ Ошибка: Не найдено проектов")
            return
        
        print(f"✅ Найдено проектов: {len(projects)}")
        for i, project in enumerate(projects[:5], 1):
            print(f"   {i}. {project.get('name', 'N/A')} (ID: {project.get('id', 'N/A')}, viewMode: {project.get('viewMode', 'N/A')})")
        
        # 3. Найти проект с Kanban viewMode или любой проект с колонками
        print("\n[3/7] Поиск проекта с колонками (Kanban)...")
        target_project = None
        for project in projects:
            view_mode = project.get('viewMode', '').lower()
            if view_mode == 'kanban':
                target_project = project
                print(f"✅ Найден Kanban проект: {project.get('name')} (ID: {project.get('id')})")
                break
        
        # Если нет Kanban, берем первый проект и проверяем колонки
        if not target_project:
            target_project = projects[0]
            print(f"⚠️  Kanban проект не найден, используем первый проект: {target_project.get('name')} (ID: {target_project.get('id')})")
        
        project_id = target_project.get('id')
        
        # 4. Получить данные проекта (включая колонки)
        print(f"\n[4/7] Получение данных проекта {target_project.get('name')}...")
        project_data = await client.get(
            endpoint=f"/open/v1/project/{project_id}/data",
            headers=client._get_headers(),
        )
        
        if not project_data:
            print("❌ Ошибка: Не удалось получить данные проекта")
            return
        
        columns = project_data.get('columns', [])
        tasks = project_data.get('tasks', [])
        
        print(f"✅ Получены данные проекта:")
        print(f"   - Колонок: {len(columns)}")
        print(f"   - Задач: {len(tasks)}")
        
        if columns:
            print("\n   Колонки:")
            for i, column in enumerate(columns, 1):
                print(f"   {i}. {column.get('name', 'N/A')} (ID: {column.get('id', 'N/A')})")
        else:
            print("⚠️  Колонки не найдены (возможно, проект в режиме 'list', а не 'kanban')")
        
        # 5. Найти колонку "в процессе" или использовать первую
        print("\n[5/7] Поиск колонки 'в процессе'...")
        target_column = None
        
        # Варианты названий для поиска
        search_names = ['в процессе', 'в процессе', 'in progress', 'in_progress', 'процесс']
        
        for column in columns:
            column_name = column.get('name', '').lower()
            for search_name in search_names:
                if search_name in column_name:
                    target_column = column
                    print(f"✅ Найдена колонка: {column.get('name')} (ID: {column.get('id')})")
                    break
            if target_column:
                break
        
        if not target_column and columns:
            target_column = columns[0]
            print(f"⚠️  Колонка 'в процессе' не найдена, используем первую: {target_column.get('name')} (ID: {target_column.get('id')})")
        
        if not target_column:
            print("❌ Ошибка: Нет колонок для тестирования")
            return
        
        column_id = target_column.get('id')
        column_name = target_column.get('name')
        
        # 6. Найти или создать тестовую задачу
        print(f"\n[6/7] Поиск тестовой задачи...")
        test_task = None
        
        if tasks:
            # Используем первую задачу
            test_task = tasks[0]
            print(f"✅ Найдена задача: {test_task.get('title', 'N/A')} (ID: {test_task.get('id', 'N/A')})")
        else:
            # Создаем тестовую задачу
            print("   Создание тестовой задачи для теста...")
            try:
                new_task = await client.create_task(
                    title="ТЕСТ: Задача для проверки columnId",
                    project_id=project_id,
                )
                test_task = new_task
                print(f"✅ Создана тестовая задача: {test_task.get('title', 'N/A')} (ID: {test_task.get('id', 'N/A')})")
            except Exception as e:
                print(f"❌ Ошибка создания задачи: {e}")
                return
        
        task_id = test_task.get('id')
        current_column_id = test_task.get('columnId')  # Проверяем, есть ли уже columnId
        
        print(f"\n   Текущее состояние задачи:")
        print(f"   - ID: {task_id}")
        print(f"   - Название: {test_task.get('title', 'N/A')}")
        print(f"   - Текущий columnId: {current_column_id or 'не указан'}")
        
        # 7. Попробовать обновить задачу с columnId
        print(f"\n[7/7] Тестирование обновления задачи с columnId...")
        print(f"   Пытаемся установить columnId = {column_id} (колонка: {column_name})")
        
        try:
            # Получаем текущие данные задачи для полного обновления
            current_task_data = await client.get(
                endpoint=f"/open/v1/project/{project_id}/task/{task_id}",
                headers=client._get_headers(),
            )
            
            if not current_task_data:
                print("❌ Ошибка: Не удалось получить текущие данные задачи")
                return
            
            # Подготавливаем данные для обновления
            update_data = {
                "id": task_id,
                "projectId": project_id,
                "title": current_task_data.get('title', test_task.get('title')),
            }
            
            # Пробуем добавить columnId
            update_data["columnId"] = column_id
            
            # Копируем другие важные поля
            for field in ['priority', 'tags', 'content', 'dueDate', 'startDate', 'status']:
                if field in current_task_data:
                    update_data[field] = current_task_data[field]
            
            print(f"\n   Отправляем запрос на обновление:")
            print(f"   {json.dumps(update_data, indent=2, ensure_ascii=False)}")
            
            # Отправляем запрос
            result = await client.post(
                endpoint=f"/open/v1/task/{task_id}",
                headers=client._get_headers(),
                json_data=update_data,
            )
            
            print(f"\n✅ Запрос отправлен успешно!")
            print(f"   Ответ API:")
            print(f"   {json.dumps(result, indent=2, ensure_ascii=False)}")
            
            # Проверяем результат
            if isinstance(result, dict):
                returned_column_id = result.get('columnId')
                if returned_column_id:
                    print(f"\n🎉 УСПЕХ! API вернул columnId: {returned_column_id}")
                    if returned_column_id == column_id:
                        print(f"✅ columnId совпадает с запрошенным!")
                    else:
                        print(f"⚠️  columnId отличается от запрошенного (запрошено: {column_id}, получено: {returned_column_id})")
                else:
                    print(f"\n⚠️  API не вернул columnId в ответе")
                    print(f"   Проверьте, изменилась ли колонка задачи в TickTick приложении")
            else:
                print(f"\n⚠️  Неожиданный формат ответа: {type(result)}")
            
            # Проверяем, изменилась ли задача, запросив её снова
            print(f"\n   Проверка изменений (запрос задачи снова)...")
            await asyncio.sleep(2)  # Небольшая задержка для синхронизации
            
            updated_task = await client.get(
                endpoint=f"/open/v1/project/{project_id}/task/{task_id}",
                headers=client._get_headers(),
            )
            
            if updated_task:
                updated_column_id = updated_task.get('columnId')
                print(f"   Обновленный columnId: {updated_column_id or 'не указан'}")
                if updated_column_id == column_id:
                    print(f"✅ ПОДТВЕРЖДЕНО: Задача успешно перенесена в колонку '{column_name}'!")
                elif updated_column_id:
                    print(f"⚠️  columnId изменился, но не на запрошенный (текущий: {updated_column_id})")
                else:
                    print(f"⚠️  columnId не установлен (возможно, API не поддерживает это поле)")
            
        except Exception as e:
            print(f"\n❌ Ошибка при обновлении задачи: {e}")
            import traceback
            traceback.print_exc()
            return
        
        print("\n" + "=" * 80)
        print("ТЕСТ ЗАВЕРШЕН")
        print("=" * 80)
        
    except Exception as e:
        print(f"\n❌ Критическая ошибка: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_column_id_support())



