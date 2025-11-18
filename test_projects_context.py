#!/usr/bin/env python3
"""Test script to check how projects are fetched and passed to GPT"""
import asyncio
import sys
from pathlib import Path
import json

project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.api.ticktick_client import TickTickClient
from src.services.gpt_service import GPTService

async def test_projects_context():
    """Test how projects are fetched and formatted for GPT"""
    print("=" * 60)
    print("Тест получения проектов и передачи в GPT")
    print("=" * 60)
    
    # 1. Test TickTick API
    print("\n1. Тестирование TickTick API get_projects()...")
    client = TickTickClient()
    await client.authenticate()
    print("✅ TickTick client authenticated")
    
    try:
        projects = await client.get_projects()
        print(f"✅ Получено проектов из API: {len(projects)}")
        
        if projects:
            print("\n📋 Первые 5 проектов из API:")
            for i, project in enumerate(projects[:5], 1):
                print(f"   {i}. {json.dumps(project, indent=6, ensure_ascii=False)}")
            
            # Check structure
            first_project = projects[0]
            print(f"\n🔍 Структура первого проекта:")
            print(f"   - Тип: {type(first_project)}")
            print(f"   - Ключи: {list(first_project.keys()) if isinstance(first_project, dict) else 'N/A'}")
            if isinstance(first_project, dict):
                print(f"   - id: {first_project.get('id', 'MISSING')}")
                print(f"   - name: {first_project.get('name', 'MISSING')}")
        else:
            print("⚠️  Проекты не получены или список пуст")
            
    except Exception as e:
        print(f"❌ Ошибка получения проектов: {e}")
        import traceback
        traceback.print_exc()
    
    # 2. Test GPT Service context
    print("\n\n2. Тестирование GPT Service _get_context_for_parsing()...")
    gpt_service = GPTService(ticktick_client=client)
    
    try:
        context = await gpt_service._get_context_for_parsing()
        print(f"✅ Контекст получен")
        print(f"   - Ключи контекста: {list(context.keys())}")
        print(f"   - Количество проектов в контексте: {len(context.get('projects', []))}")
        
        if context.get('projects'):
            print("\n📋 Проекты в контексте для GPT:")
            for i, project in enumerate(context['projects'][:5], 1):
                print(f"   {i}. {json.dumps(project, indent=6, ensure_ascii=False)}")
            
            # Check if IDs are present
            print("\n🔍 Проверка наличия ID:")
            for project in context['projects'][:5]:
                project_id = project.get('id', '')
                project_name = project.get('name', '')
                if project_id:
                    print(f"   ✅ '{project_name}' -> ID: '{project_id}'")
                else:
                    print(f"   ❌ '{project_name}' -> ID ОТСУТСТВУЕТ!")
        else:
            print("⚠️  Проекты отсутствуют в контексте")
            
    except Exception as e:
        print(f"❌ Ошибка получения контекста: {e}")
        import traceback
        traceback.print_exc()
    
    # 3. Test how it's formatted in openai_client
    print("\n\n3. Тестирование форматирования для GPT в openai_client...")
    from src.api.openai_client import OpenAIClient
    
    openai_client = OpenAIClient()
    
    context_info = await gpt_service._get_context_for_parsing()
    
    if context_info and context_info.get("projects"):
        projects_list = context_info["projects"]
        projects_text = "\n".join([
            f"  - {p.get('name', '')} (ID: {p.get('id', '')}, поиск: '{p.get('name_clean', p.get('name', ''))}')"
            for p in projects_list
        ])
        
        print("📝 Форматированный текст для GPT:")
        print("-" * 60)
        print(f"ДОСТУПНЫЕ СПИСКИ ПРОЕКТОВ:\n{projects_text[:500]}")
        if len(projects_text) > 500:
            print("... (обрезано)")
        print("-" * 60)
        
        # Check if IDs are in the formatted text
        print("\n🔍 Проверка наличия ID в форматированном тексте:")
        for project in projects_list[:5]:
            project_id = project.get('id', '')
            project_name = project.get('name', '')
            if project_id and project_id in projects_text:
                print(f"   ✅ ID '{project_id}' для '{project_name}' найден в тексте")
            else:
                print(f"   ❌ ID для '{project_name}' НЕ найден в тексте!")
    
    print("\n" + "=" * 60)
    print("Тест завершен")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(test_projects_context())

