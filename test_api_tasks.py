#!/usr/bin/env python3
"""
Тестовый скрипт для проверки получения всех задач через TickTick API
"""

import asyncio
import httpx
import json

ACCESS_TOKEN = "tp_129f30f9ec524ded813233f2e4b94083"
BASE_URL = "https://api.ticktick.com"
API_VERSION = "v1"

async def get_projects():
    """Получить все проекты"""
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{BASE_URL}/open/{API_VERSION}/project",
            headers={"Authorization": f"Bearer {ACCESS_TOKEN}"}
        )
        if response.status_code == 200:
            return response.json()
        else:
            print(f"Error getting projects: {response.status_code} - {response.text}")
            return []

async def get_project_data(project_id):
    """Получить данные проекта (включая задачи)"""
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{BASE_URL}/open/{API_VERSION}/project/{project_id}/data",
            headers={"Authorization": f"Bearer {ACCESS_TOKEN}"}
        )
        if response.status_code == 200:
            return response.json()
        else:
            print(f"Error getting project {project_id} data: {response.status_code} - {response.text}")
            return None

async def get_task_by_id(project_id, task_id):
    """Получить конкретную задачу по ID"""
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{BASE_URL}/open/{API_VERSION}/project/{project_id}/task/{task_id}",
            headers={"Authorization": f"Bearer {ACCESS_TOKEN}"}
        )
        if response.status_code == 200:
            return response.json()
        else:
            print(f"Error getting task {task_id}: {response.status_code} - {response.text}")
            return None

async def main():
    print("=" * 80)
    print("ПОЛУЧЕНИЕ ВСЕХ ПРОЕКТОВ")
    print("=" * 80)
    
    projects = await get_projects()
    print(f"\nПолучено проектов: {len(projects)}")
    
    print("\nДетали проектов:")
    for i, project in enumerate(projects, 1):
        print(f"\n{i}. {project.get('name', 'N/A')}")
        print(f"   ID: {project.get('id', 'N/A')}")
        print(f"   Kind: {project.get('kind', 'N/A')}")
        print(f"   Closed: {project.get('closed', False)}")
        print(f"   ViewMode: {project.get('viewMode', 'N/A')}")
    
    print("\n" + "=" * 80)
    print("ПОЛУЧЕНИЕ ЗАДАЧ ИЗ ВСЕХ ПРОЕКТОВ")
    print("=" * 80)
    
    all_tasks = []
    task_titles = []
    
    for project in projects:
        project_id = project.get('id')
        project_name = project.get('name', 'N/A')
        project_kind = project.get('kind', 'TASK')
        
        if project_kind == "NOTE":
            print(f"\n⚠ Пропускаем NOTE проект: {project_name}")
            continue
        
        print(f"\n📁 Проект: {project_name} (ID: {project_id})")
        
        project_data = await get_project_data(project_id)
        if project_data and 'tasks' in project_data:
            tasks = project_data['tasks']
            print(f"   Задач в проекте: {len(tasks)}")
            
            for task in tasks:
                task_title = task.get('title', 'Без названия')
                task_id = task.get('id', 'N/A')
                task_status = task.get('status', 0)
                status_text = "Завершена" if task_status == 2 else "Активна"
                
                all_tasks.append(task)
                task_titles.append(task_title)
                
                print(f"   - [{status_text}] {task_title} (ID: {task_id})")
        else:
            print(f"   ⚠ Нет задач или ошибка получения данных")
    
    print("\n" + "=" * 80)
    print("ИТОГОВЫЙ СПИСОК ВСЕХ ЗАДАЧ")
    print("=" * 80)
    print(f"\nВсего задач: {len(all_tasks)}")
    print(f"\nВсе названия задач:")
    for i, title in enumerate(task_titles, 1):
        print(f"{i}. {title}")
    
    # Проверяем наличие конкретной задачи
    print("\n" + "=" * 80)
    print("ПОИСК ЗАДАЧИ 'Тест только dueDate'")
    print("=" * 80)
    
    search_title = "Тест только dueDate"
    found = False
    
    for task in all_tasks:
        task_title = task.get('title', '')
        if search_title.lower() in task_title.lower() or task_title.lower() in search_title.lower():
            print(f"\n✓ НАЙДЕНА ЗАДАЧА:")
            print(f"   Название: {task_title}")
            print(f"   ID: {task.get('id')}")
            print(f"   Project ID: {task.get('projectId')}")
            print(f"   Status: {task.get('status', 0)}")
            print(f"   Due Date: {task.get('dueDate', 'Не указана')}")
            found = True
    
    if not found:
        print(f"\n✗ Задача '{search_title}' НЕ НАЙДЕНА в списке всех задач")
        print(f"\nВозможные причины:")
        print("1. Задача завершена (status=2) - GET /project/{id}/data возвращает только незавершенные")
        print("2. Задача в проекте, который не возвращается get_projects()")
        print("3. Задача в NOTE проекте")
        print("4. Задача в закрытом проекте (closed=true)")
        print("5. Название задачи отличается от ожидаемого")
    
    print("\n" + "=" * 80)

if __name__ == "__main__":
    asyncio.run(main())








