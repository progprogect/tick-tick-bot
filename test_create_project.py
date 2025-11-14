#!/usr/bin/env python3
"""Test for creating projects in TickTick API"""
import asyncio
import sys
from pathlib import Path

project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.api.ticktick_client import TickTickClient

async def test_create_project():
    """Test creating a project via TickTick API"""
    print("=" * 60)
    print("Тест создания проекта в TickTick API")
    print("=" * 60)
    
    client = TickTickClient()
    await client.authenticate()
    print("✅ TickTick client authenticated")
    
    # Check if create_project method exists
    if hasattr(client, 'create_project'):
        print("\n✅ Метод create_project существует")
        try:
            # Test creating a project with only name
            test_project_name = "Test Project API"
            result = await client.create_project(name=test_project_name)
            print(f"\n✅ Проект создан:")
            print(f"   ID: {result.get('id', 'N/A')}")
            print(f"   Name: {result.get('name', 'N/A')}")
            print(f"   Color: {result.get('color', 'N/A')}")
            print(f"   ViewMode: {result.get('viewMode', 'N/A')}")
            print(f"   Kind: {result.get('kind', 'N/A')}")
            
            # Test creating a project with optional parameters
            print("\n" + "=" * 60)
            print("Тест создания проекта с опциональными параметрами")
            print("=" * 60)
            test_project_name2 = "Test Project with Options"
            result2 = await client.create_project(
                name=test_project_name2,
                color="#F18181",
                view_mode="list",
                kind="TASK"
            )
            print(f"\n✅ Проект создан с параметрами:")
            print(f"   ID: {result2.get('id', 'N/A')}")
            print(f"   Name: {result2.get('name', 'N/A')}")
            print(f"   Color: {result2.get('color', 'N/A')}")
            print(f"   ViewMode: {result2.get('viewMode', 'N/A')}")
            print(f"   Kind: {result2.get('kind', 'N/A')}")
            
        except Exception as e:
            print(f"\n❌ Ошибка создания проекта: {str(e)[:300]}")
            import traceback
            traceback.print_exc()
    else:
        print("\n❌ Метод create_project НЕ существует")
        print("   Нужно реализовать метод согласно документации TickTick API")
        
        # Check current projects
        print("\nПроверка существующих проектов...")
        try:
            projects = await client.get_projects()
            print(f"✅ Получено проектов: {len(projects)}")
            if projects:
                print(f"   Пример: {projects[0].get('name', 'N/A')}")
        except Exception as e:
            print(f"❌ Ошибка получения проектов: {str(e)[:300]}")

if __name__ == "__main__":
    asyncio.run(test_create_project())

