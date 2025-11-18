#!/usr/bin/env python3
"""
Simple test script for bot functionality
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from src.api.ticktick_client import TickTickClient
from src.api.openai_client import OpenAIClient
from src.services.gpt_service import GPTService
from src.services.task_manager import TaskManager
from src.services.tag_manager import TagManager
from src.services.note_manager import NoteManager
from src.services.recurring_task_manager import RecurringTaskManager
from src.services.reminder_manager import ReminderManager
from src.services.analytics_service import AnalyticsService
from src.utils.logger import logger
from src.config.settings import settings


async def test_basic_functionality():
    """Test basic bot functionality"""
    print("=" * 60)
    print("Testing TickTick Bot Functionality")
    print("=" * 60)
    
    results = {
        "passed": [],
        "failed": [],
        "errors": []
    }
    
    try:
        # Initialize clients
        print("\n1. Initializing clients...")
        ticktick_client = TickTickClient()
        openai_client = OpenAIClient()
        gpt_service = GPTService()
        
        # Test authentication
        print("2. Testing TickTick authentication...")
        auth_result = await ticktick_client.authenticate()
        if auth_result:
            print("   ✅ Authentication successful")
            results["passed"].append("TickTick Authentication")
        else:
            print("   ❌ Authentication failed")
            results["failed"].append("TickTick Authentication")
        
        # Test OpenAI connection
        print("3. Testing OpenAI connection...")
        try:
            # Simple test - just check if we can create a client
            test_messages = [
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": "Say 'test'"}
            ]
            response = await openai_client.chat_completion(test_messages, max_tokens=10)
            if "test" in response.lower():
                print("   ✅ OpenAI connection successful")
                results["passed"].append("OpenAI Connection")
            else:
                print("   ⚠️ OpenAI connection works but response unexpected")
                results["passed"].append("OpenAI Connection")
        except Exception as e:
            print(f"   ❌ OpenAI connection failed: {e}")
            results["failed"].append(f"OpenAI Connection: {str(e)}")
        
        # Test GPT command parsing
        print("4. Testing GPT command parsing...")
        try:
            test_command = "Создай задачу купить молоко"
            parsed = await gpt_service.parse_command(test_command)
            if parsed.action == "create_task" and parsed.title:
                print(f"   ✅ Command parsing successful: {parsed.action} - {parsed.title}")
                results["passed"].append("GPT Command Parsing")
            else:
                print(f"   ⚠️ Command parsed but unexpected: {parsed}")
                results["failed"].append("GPT Command Parsing")
        except Exception as e:
            print(f"   ❌ Command parsing failed: {e}")
            results["failed"].append(f"GPT Command Parsing: {str(e)}")
        
        # Test Task Manager
        print("5. Testing Task Manager...")
        task_manager = TaskManager(ticktick_client)
        try:
            # Try to get tasks (read-only operation)
            tasks = await ticktick_client.get_tasks()
            print(f"   ✅ Task Manager initialized, found {len(tasks)} tasks")
            results["passed"].append("Task Manager")
        except Exception as e:
            print(f"   ⚠️ Task Manager error: {e}")
            results["errors"].append(f"Task Manager: {str(e)}")
        
        # Test other managers initialization
        print("6. Testing other managers...")
        try:
            tag_manager = TagManager(ticktick_client)
            note_manager = NoteManager(ticktick_client)
            recurring_task_manager = RecurringTaskManager(ticktick_client)
            reminder_manager = ReminderManager(ticktick_client)
            analytics_service = AnalyticsService(ticktick_client, gpt_service)
            print("   ✅ All managers initialized successfully")
            results["passed"].append("Managers Initialization")
        except Exception as e:
            print(f"   ❌ Managers initialization failed: {e}")
            results["failed"].append(f"Managers Initialization: {str(e)}")
        
        # Cleanup
        await ticktick_client.close()
        
    except Exception as e:
        print(f"\n❌ Critical error: {e}")
        logger.error(f"Test error: {e}", exc_info=True)
        results["errors"].append(f"Critical: {str(e)}")
    
    # Print summary
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)
    print(f"✅ Passed: {len(results['passed'])}")
    print(f"❌ Failed: {len(results['failed'])}")
    print(f"⚠️ Errors: {len(results['errors'])}")
    
    if results["passed"]:
        print("\nPassed tests:")
        for test in results["passed"]:
            print(f"  ✅ {test}")
    
    if results["failed"]:
        print("\nFailed tests:")
        for test in results["failed"]:
            print(f"  ❌ {test}")
    
    if results["errors"]:
        print("\nErrors:")
        for error in results["errors"]:
            print(f"  ⚠️ {error}")
    
    return results


if __name__ == "__main__":
    asyncio.run(test_basic_functionality())











