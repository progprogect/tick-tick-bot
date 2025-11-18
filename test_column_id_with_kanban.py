"""
Тестовый скрипт для проверки поддержки columnId в TickTick API
Создает Kanban проект и проверяет перенос задач в секции
"""

import asyncio
import json
from src.api.ticktick_client import TickTickClient
from src.config.settings import settings
from src.utils.logger import logger


async def test_column_id_with_kanban():
    """Тестирует поддержку columnId, создавая Kanban проект"""
    
    print("=" * 80)
    print("ТЕСТ: Поддержка columnId для переноса задач в секции (Kanban)")
    print("=" * 80)
    
    client = TickTickClient()
    
    try:
        # 1. Аутентификация
        print("\n[1/8] Аутентификация...")
        await client.authenticate()
        if not client.access_token:
            print("❌ Ошибка: Не удалось аутентифицироваться")
            return
        print("✅ Аутентификация успешна")
        
        # 2. Создать Kanban проект для теста
        print("\n[2/8] Создание Kanban проекта для теста...")
        test_project_name = "ТЕСТ: Kanban для columnId"
        
        try:
            # Сначала проверим, не существует ли уже такой проект
            projects = await client.get_projects()
            existing_project = next((p for p in projects if p.get('name') == test_project_name), None)
            
            if existing_project:
                print(f"⚠️  Проект '{test_project_name}' уже существует, используем его")
                test_project = existing_project
                project_id = test_project.get('id')
            else:
                # Создаем новый Kanban проект
                test_project = await client.post(
                    endpoint="/open/v1/project",
                    headers=client._get_headers(),
                    json_data={
                        "name": test_project_name,
                        "viewMode": "kanban",
                        "kind": "TASK"
                    }
                )
                project_id = test_project.get('id')
                print(f"✅ Создан Kanban проект: {test_project.get('name')} (ID: {project_id})")
        except Exception as e:
            print(f"❌ Ошибка создания проекта: {e}")
            import traceback
            traceback.print_exc()
            return
        
        # 3. Получить данные проекта (включая колонки)
        print(f"\n[3/8] Получение данных проекта (включая колонки)...")
        await asyncio.sleep(1)  # Небольшая задержка для синхронизации
        
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
            print("⚠️  Колонки не найдены")
            print("   Примечание: В TickTick колонки могут создаваться автоматически при создании Kanban проекта")
            print("   или могут быть созданы вручную в приложении")
        
        # 4. Если колонок нет, попробуем создать задачу и посмотреть, появятся ли колонки
        if not columns:
            print("\n[4/8] Колонок нет, создаем задачу для инициализации колонок...")
            try:
                test_task = await client.create_task(
                    title="Тестовая задача для инициализации колонок",
                    project_id=project_id,
                )
                print(f"✅ Создана задача: {test_task.get('title')} (ID: {test_task.get('id')})")
                
                # Ждем и проверяем колонки снова
                await asyncio.sleep(2)
                project_data = await client.get(
                    endpoint=f"/open/v1/project/{project_id}/data",
                    headers=client._get_headers(),
                )
                columns = project_data.get('columns', [])
                if columns:
                    print(f"✅ Колонки появились: {len(columns)}")
                    for i, column in enumerate(columns, 1):
                        print(f"   {i}. {column.get('name', 'N/A')} (ID: {column.get('id', 'N/A')})")
                else:
                    print("⚠️  Колонки все еще не найдены")
            except Exception as e:
                print(f"⚠️  Ошибка создания задачи: {e}")
        
        # 5. Если колонок все еще нет, попробуем тест без колонок (проверим, примет ли API columnId)
        if not columns:
            print("\n[5/8] Колонок нет, но попробуем отправить columnId для проверки API...")
            print("   (API может принять columnId даже если колонок нет в ответе)")
            
            # Используем произвольный columnId для теста
            test_column_id = "test_column_id_12345"
            
            # Найдем или создадим задачу
            tasks = project_data.get('tasks', [])
            if tasks:
                test_task = tasks[0]
            else:
                test_task = await client.create_task(
                    title="Тестовая задача для проверки columnId",
                    project_id=project_id,
                )
            
            task_id = test_task.get('id')
            
            # Получаем текущие данные задачи
            current_task_data = await client.get(
                endpoint=f"/open/v1/project/{project_id}/task/{task_id}",
                headers=client._get_headers(),
            )
            
            # Пробуем отправить columnId
            update_data = {
                "id": task_id,
                "projectId": project_id,
                "title": current_task_data.get('title', test_task.get('title')),
                "columnId": test_column_id,  # Пробуем отправить columnId
            }
            
            print(f"\n   Отправляем запрос с columnId:")
            print(f"   {json.dumps(update_data, indent=2, ensure_ascii=False)}")
            
            try:
                result = await client.post(
                    endpoint=f"/open/v1/task/{task_id}",
                    headers=client._get_headers(),
                    json_data=update_data,
                )
                
                print(f"\n✅ Запрос отправлен!")
                print(f"   Ответ API:")
                print(f"   {json.dumps(result, indent=2, ensure_ascii=False)}")
                
                # Проверяем, вернул ли API columnId
                if isinstance(result, dict):
                    returned_column_id = result.get('columnId')
                    if returned_column_id:
                        print(f"\n🎉 API ПОДДЕРЖИВАЕТ columnId! Вернул: {returned_column_id}")
                    else:
                        print(f"\n⚠️  API не вернул columnId (возможно, не поддерживает или недопустимое значение)")
            except Exception as e:
                print(f"\n❌ Ошибка при отправке columnId: {e}")
                import traceback
                traceback.print_exc()
            
            print("\n" + "=" * 80)
            print("ТЕСТ ЗАВЕРШЕН (без реальных колонок)")
            print("=" * 80)
            return
        
        # 6. Найти колонку "в процессе" или использовать первую
        print("\n[6/8] Поиск колонки 'в процессе'...")
        target_column = None
        
        # Варианты названий для поиска
        search_names = ['в процессе', 'in progress', 'in_progress', 'процесс', 'doing', 'doing']
        
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
        
        # 7. Найти или создать тестовую задачу
        print(f"\n[7/8] Поиск или создание тестовой задачи...")
        test_task = None
        
        if tasks:
            # Используем первую задачу
            test_task = tasks[0]
            print(f"✅ Найдена задача: {test_task.get('title', 'N/A')} (ID: {test_task.get('id', 'N/A')})")
        else:
            # Создаем тестовую задачу
            print("   Создание тестовой задачи...")
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
        current_column_id = test_task.get('columnId')
        
        print(f"\n   Текущее состояние задачи:")
        print(f"   - ID: {task_id}")
        print(f"   - Название: {test_task.get('title', 'N/A')}")
        print(f"   - Текущий columnId: {current_column_id or 'не указан'}")
        
        # 8. Попробовать обновить задачу с columnId
        print(f"\n[8/8] Тестирование обновления задачи с columnId...")
        print(f"   Пытаемся установить columnId = {column_id} (колонка: {column_name})")
        
        try:
            # Получаем текущие данные задачи
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
                "columnId": column_id,  # Добавляем columnId
            }
            
            # Копируем другие важные поля
            for field in ['priority', 'tags', 'content', 'dueDate', 'startDate', 'status']:
                if field in current_task_data:
                    update_data[field] = current_task_data[field]
            
            print(f"\n   Отправляем запрос на обновление:")
            print(f"   {json.dumps({k: v for k, v in update_data.items() if k != 'content'}, indent=2, ensure_ascii=False)}")
            
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
                    print(f"\n🎉🎉🎉 ПОДТВЕРЖДЕНО: Задача успешно перенесена в колонку '{column_name}'!")
                    print(f"✅ API ПОДДЕРЖИВАЕТ columnId для переноса задач в секции!")
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
    asyncio.run(test_column_id_with_kanban())



