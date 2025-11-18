#!/bin/bash

TOKEN="tp_129f30f9ec524ded813233f2e4b94083"
BASE_URL="https://api.ticktick.com/open/v1"

echo "=========================================="
echo "ПОЛУЧЕНИЕ ВСЕХ ПРОЕКТОВ"
echo "=========================================="

PROJECTS=$(curl -s -H "Authorization: Bearer $TOKEN" "${BASE_URL}/project")
echo "$PROJECTS" | python3 -m json.tool

echo ""
echo "=========================================="
echo "ПОЛУЧЕНИЕ ЗАДАЧ ИЗ КАЖДОГО ПРОЕКТА"
echo "=========================================="

# Извлекаем ID проектов и получаем задачи
echo "$PROJECTS" | python3 -c "
import json
import sys
import subprocess

projects = json.load(sys.stdin)
token = '$TOKEN'
base_url = '$BASE_URL'

all_tasks = []
task_titles = []

for project in projects:
    project_id = project.get('id')
    project_name = project.get('name', 'N/A')
    project_kind = project.get('kind', 'TASK')
    project_closed = project.get('closed', False)
    
    print(f'\n📁 Проект: {project_name} (ID: {project_id}, Kind: {project_kind}, Closed: {project_closed})')
    
    if project_kind == 'NOTE':
        print('   ⚠ Пропускаем NOTE проект')
        continue
    
    # Получаем задачи из проекта
    result = subprocess.run(
        ['curl', '-s', '-H', f'Authorization: Bearer {token}', f'{base_url}/project/{project_id}/data'],
        capture_output=True,
        text=True
    )
    
    if result.returncode == 0:
        try:
            project_data = json.loads(result.stdout)
            tasks = project_data.get('tasks', [])
            print(f'   Задач в проекте: {len(tasks)}')
            
            for task in tasks:
                title = task.get('title', 'Без названия')
                task_id = task.get('id', 'N/A')
                status = task.get('status', 0)
                status_text = 'Завершена' if status == 2 else 'Активна'
                
                all_tasks.append(task)
                task_titles.append(title)
                
                print(f'   - [{status_text}] {title} (ID: {task_id})')
        except json.JSONDecodeError as e:
            print(f'   ⚠ Ошибка парсинга JSON: {e}')
            print(f'   Ответ: {result.stdout[:200]}')
    else:
        print(f'   ⚠ Ошибка получения данных: {result.stderr}')

print('\n==========================================')
print('ИТОГОВЫЙ СПИСОК ВСЕХ ЗАДАЧ')
print('==========================================')
print(f'\nВсего задач: {len(all_tasks)}')
print(f'\nВсе названия задач:')
for i, title in enumerate(task_titles, 1):
    print(f'{i}. {title}')

# Поиск конкретной задачи
search_title = 'Тест только dueDate'
print(f'\n==========================================')
print(f'ПОИСК ЗАДАЧИ: {search_title}')
print('==========================================')

found = False
for task in all_tasks:
    task_title = task.get('title', '')
    if search_title.lower() in task_title.lower() or task_title.lower() in search_title.lower():
        print(f'\n✓ НАЙДЕНА ЗАДАЧА:')
        print(f'   Название: {task_title}')
        print(f'   ID: {task.get(\"id\")}')
        print(f'   Project ID: {task.get(\"projectId\")}')
        print(f'   Status: {task.get(\"status\", 0)}')
        print(f'   Due Date: {task.get(\"dueDate\", \"Не указана\")}')
        found = True

if not found:
    print(f'\n✗ Задача \"{search_title}\" НЕ НАЙДЕНА в списке всех задач')
    print(f'\nВозможные причины:')
    print('1. Задача завершена (status=2) - GET /project/{id}/data возвращает только незавершенные')
    print('2. Задача в проекте, который не возвращается get_projects()')
    print('3. Задача в NOTE проекте')
    print('4. Задача в закрытом проекте (closed=true)')
    print('5. Название задачи отличается от ожидаемого')
"





