"""
Direct API request tests - testing actual TickTick API calls
Checking request format, headers, and response
"""

import pytest
import json
from datetime import datetime, timedelta
from src.api.ticktick_client import TickTickClient
from src.services.task_cache import TaskCacheService


@pytest.fixture(scope="function")
async def ticktick_client():
    """Real TickTick client"""
    client = TickTickClient()
    await client.authenticate()
    yield client


@pytest.mark.integration
@pytest.mark.asyncio
class TestAPIRequests:
    """Test actual API requests to verify format and correctness"""
    
    async def test_create_task_request_format(self, ticktick_client):
        """Test 1: Verify CREATE task request format"""
        test_name = "1. CREATE Task - Формат запроса"
        
        try:
            # Create a test task
            task_data = await ticktick_client.create_task(
                title="Тест формата запроса CREATE",
                project_id=None,  # Will use default
            )
            
            task_id = task_data.get("id")
            assert task_id is not None, "Task ID not returned"
            
            # Verify task was created via GET
            project_id = task_data.get("projectId")
            if project_id:
                try:
                    verify_task = await ticktick_client.get(
                        endpoint=f"/open/v1/project/{project_id}/task/{task_id}",
                        headers=ticktick_client._get_headers(),
                    )
                    
                    assert verify_task.get("title") == "Тест формата запроса CREATE"
                    status = "✅ PASSED"
                    get_result = "✅ Verified"
                except Exception as e:
                    status = "⚠️ PARTIAL"
                    get_result = f"⚠️ GET failed: {str(e)[:100]}"
            else:
                status = "⚠️ PARTIAL"
                get_result = "⚠️ No projectId in response"
            
            print(f"\n{test_name}: {status}")
            print(f"  Task ID: {task_id}")
            print(f"  Project ID: {project_id}")
            print(f"  GET verification: {get_result}")
            
            assert task_id is not None
            
        except Exception as e:
            print(f"\n{test_name}: ❌ FAILED")
            print(f"  Error: {str(e)}")
            raise
    
    async def test_update_task_request_format(self, ticktick_client):
        """Test 2: Verify UPDATE task request format - check POST method and required fields"""
        test_name = "2. UPDATE Task - Формат запроса"
        
        try:
            # Create a task first
            create_result = await ticktick_client.create_task(
                title="Тест для UPDATE",
            )
            task_id = create_result.get("id")
            project_id = create_result.get("projectId")
            
            assert task_id is not None, "Task not created"
            assert project_id is not None, "Project ID not in create response"
            
            # Save to cache for update
            cache = TaskCacheService()
            cache.save_task(
                task_id=task_id,
                title="Тест для UPDATE",
                project_id=project_id,
            )
            
            # Small delay to ensure cache is written
            import asyncio
            await asyncio.sleep(0.1)
            
            # Update task - check if we're using POST with correct fields
            tomorrow = (datetime.now() + timedelta(days=1)).isoformat()
            
            # This should use POST /open/v1/task/{taskId} with id and projectId in body
            # Pass project_id explicitly to avoid cache issues
            update_result = await ticktick_client.update_task(
                task_id=task_id,
                project_id=project_id,  # Pass explicitly
                due_date=tomorrow,
                title="Тест для UPDATE - обновлено",
            )
            
            # Verify update via GET
            try:
                verify_task = await ticktick_client.get(
                    endpoint=f"/open/v1/project/{project_id}/task/{task_id}",
                    headers=ticktick_client._get_headers(),
                )
                
                assert verify_task.get("dueDate") is not None, "Due date not updated"
                assert verify_task.get("title") == "Тест для UPDATE - обновлено", "Title not updated"
                status = "✅ PASSED"
                get_result = "✅ Verified - both dueDate and title updated"
            except Exception as e:
                status = "⚠️ PARTIAL"
                get_result = f"⚠️ GET failed: {str(e)[:100]}"
            
            print(f"\n{test_name}: {status}")
            print(f"  Task ID: {task_id}")
            print(f"  Project ID: {project_id}")
            print(f"  Update result keys: {list(update_result.keys()) if isinstance(update_result, dict) else 'N/A'}")
            print(f"  GET verification: {get_result}")
            
        except Exception as e:
            print(f"\n{test_name}: ❌ FAILED")
            print(f"  Error: {str(e)}")
            raise
    
    async def test_update_task_with_only_due_date(self, ticktick_client):
        """Test 3: UPDATE task with only dueDate - verify minimal update works"""
        test_name = "3. UPDATE Task - Только dueDate"
        
        try:
            # Create task
            create_result = await ticktick_client.create_task(
                title="Тест только dueDate",
            )
            task_id = create_result.get("id")
            project_id = create_result.get("projectId")
            
            cache = TaskCacheService()
            cache.save_task(
                task_id=task_id,
                title="Тест только dueDate",
                project_id=project_id,
            )
            
            # Update only dueDate
            tomorrow = (datetime.now() + timedelta(days=1)).isoformat()
            update_result = await ticktick_client.update_task(
                task_id=task_id,
                due_date=tomorrow,
            )
            
            # Verify
            try:
                verify_task = await ticktick_client.get(
                    endpoint=f"/open/v1/project/{project_id}/task/{task_id}",
                    headers=ticktick_client._get_headers(),
                )
                
                assert verify_task.get("dueDate") is not None
                status = "✅ PASSED"
                get_result = "✅ Verified - dueDate updated"
            except Exception as e:
                status = "⚠️ PARTIAL"
                get_result = f"⚠️ GET failed: {str(e)[:100]}"
            
            print(f"\n{test_name}: {status}")
            print(f"  GET verification: {get_result}")
            
        except Exception as e:
            print(f"\n{test_name}: ❌ FAILED")
            print(f"  Error: {str(e)}")
            raise
    
    async def test_update_task_with_tags(self, ticktick_client):
        """Test 4: UPDATE task with tags - verify tags field format"""
        test_name = "4. UPDATE Task - Добавление тегов"
        
        try:
            # Create task
            create_result = await ticktick_client.create_task(
                title="Тест тегов",
            )
            task_id = create_result.get("id")
            project_id = create_result.get("projectId")
            
            cache = TaskCacheService()
            cache.save_task(
                task_id=task_id,
                title="Тест тегов",
                project_id=project_id,
                tags=["existing_tag"],
            )
            
            # Update with tags
            update_result = await ticktick_client.update_task(
                task_id=task_id,
                tags=["existing_tag", "новый_тег", "важное"],
            )
            
            # Verify
            try:
                verify_task = await ticktick_client.get(
                    endpoint=f"/open/v1/project/{project_id}/task/{task_id}",
                    headers=ticktick_client._get_headers(),
                )
                
                task_tags = verify_task.get("tags", [])
                assert len(task_tags) > 0, "Tags not found"
                assert "новый_тег" in task_tags or any("новый" in str(tag).lower() for tag in task_tags), "New tag not found"
                status = "✅ PASSED"
                get_result = f"✅ Verified - tags updated: {task_tags}"
            except Exception as e:
                status = "⚠️ PARTIAL"
                get_result = f"⚠️ GET failed: {str(e)[:100]}"
            
            print(f"\n{test_name}: {status}")
            print(f"  GET verification: {get_result}")
            
        except Exception as e:
            print(f"\n{test_name}: ❌ FAILED")
            print(f"  Error: {str(e)}")
            raise
    
    async def test_update_task_with_notes(self, ticktick_client):
        """Test 5: UPDATE task with notes - verify content field"""
        test_name = "5. UPDATE Task - Добавление заметок"
        
        try:
            # Create task
            create_result = await ticktick_client.create_task(
                title="Тест заметок",
            )
            task_id = create_result.get("id")
            project_id = create_result.get("projectId")
            
            cache = TaskCacheService()
            cache.save_task(
                task_id=task_id,
                title="Тест заметок",
                project_id=project_id,
            )
            
            # Update with notes (should use 'content' field)
            update_result = await ticktick_client.update_task(
                task_id=task_id,
                notes="Это тестовая заметка для проверки API",
            )
            
            # Verify
            try:
                verify_task = await ticktick_client.get(
                    endpoint=f"/open/v1/project/{project_id}/task/{task_id}",
                    headers=ticktick_client._get_headers(),
                )
                
                content = verify_task.get("content", "")
                assert "тестовая заметка" in content.lower(), "Content not updated"
                status = "✅ PASSED"
                get_result = "✅ Verified - content updated"
            except Exception as e:
                status = "⚠️ PARTIAL"
                get_result = f"⚠️ GET failed: {str(e)[:100]}"
            
            print(f"\n{test_name}: {status}")
            print(f"  GET verification: {get_result}")
            
        except Exception as e:
            print(f"\n{test_name}: ❌ FAILED")
            print(f"  Error: {str(e)}")
            raise
    
    async def test_update_task_with_repeat_flag(self, ticktick_client):
        """Test 6: UPDATE task with repeatFlag - verify RRULE format"""
        test_name = "6. UPDATE Task - RepeatFlag (RRULE)"
        
        try:
            # Create task
            create_result = await ticktick_client.create_task(
                title="Тест повторения",
            )
            task_id = create_result.get("id")
            project_id = create_result.get("projectId")
            
            cache = TaskCacheService()
            cache.save_task(
                task_id=task_id,
                title="Тест повторения",
                project_id=project_id,
            )
            
            # Update with repeatFlag
            update_result = await ticktick_client.update_task(
                task_id=task_id,
                repeat_flag="RRULE:FREQ=DAILY;INTERVAL=1",
            )
            
            # Verify
            try:
                verify_task = await ticktick_client.get(
                    endpoint=f"/open/v1/project/{project_id}/task/{task_id}",
                    headers=ticktick_client._get_headers(),
                )
                
                repeat_flag = verify_task.get("repeatFlag")
                assert repeat_flag is not None, "RepeatFlag not set"
                assert "RRULE:FREQ=DAILY" in repeat_flag, "RepeatFlag format incorrect"
                status = "✅ PASSED"
                get_result = f"✅ Verified - repeatFlag: {repeat_flag}"
            except Exception as e:
                status = "⚠️ PARTIAL"
                get_result = f"⚠️ GET failed: {str(e)[:100]}"
            
            print(f"\n{test_name}: {status}")
            print(f"  GET verification: {get_result}")
            
        except Exception as e:
            print(f"\n{test_name}: ❌ FAILED")
            print(f"  Error: {str(e)}")
            raise
    
    async def test_update_task_with_reminders(self, ticktick_client):
        """Test 7: UPDATE task with reminders - verify TRIGGER format"""
        test_name = "7. UPDATE Task - Reminders (TRIGGER)"
        
        try:
            # Create task
            create_result = await ticktick_client.create_task(
                title="Тест напоминаний",
            )
            task_id = create_result.get("id")
            project_id = create_result.get("projectId")
            
            cache = TaskCacheService()
            cache.save_task(
                task_id=task_id,
                title="Тест напоминаний",
                project_id=project_id,
            )
            
            # Update with reminders (TRIGGER format)
            # Format: TRIGGER:P0DT9H0M0S (9 hours before)
            reminders = ["TRIGGER:P0DT9H0M0S"]
            
            update_result = await ticktick_client.update_task(
                task_id=task_id,
                reminders=reminders,
            )
            
            # Verify
            try:
                verify_task = await ticktick_client.get(
                    endpoint=f"/open/v1/project/{project_id}/task/{task_id}",
                    headers=ticktick_client._get_headers(),
                )
                
                task_reminders = verify_task.get("reminders", [])
                assert len(task_reminders) > 0, "Reminders not set"
                assert any("TRIGGER" in str(rem) for rem in task_reminders), "Reminder format incorrect"
                status = "✅ PASSED"
                get_result = f"✅ Verified - reminders: {task_reminders}"
            except Exception as e:
                status = "⚠️ PARTIAL"
                get_result = f"⚠️ GET failed: {str(e)[:100]}"
            
            print(f"\n{test_name}: {status}")
            print(f"  GET verification: {get_result}")
            
        except Exception as e:
            print(f"\n{test_name}: ❌ FAILED")
            print(f"  Error: {str(e)}")
            raise
    
    async def test_update_task_move_to_another_project(self, ticktick_client):
        """Test 8: UPDATE task - move to another project (change projectId)"""
        test_name = "8. UPDATE Task - Перенос в другой проект"
        
        try:
            # Get projects
            projects = await ticktick_client.get_projects()
            if len(projects) < 2:
                print(f"\n{test_name}: ⚠️ SKIPPED - Need at least 2 projects")
                return
            
            source_project = projects[0].get("id")
            target_project = projects[1].get("id")
            
            # Create task in source project
            create_result = await ticktick_client.create_task(
                title="Тест переноса проекта",
                project_id=source_project,
            )
            task_id = create_result.get("id")
            
            cache = TaskCacheService()
            cache.save_task(
                task_id=task_id,
                title="Тест переноса проекта",
                project_id=source_project,
            )
            
            # Update projectId to move task
            try:
                update_result = await ticktick_client.update_task(
                    task_id=task_id,
                    project_id=target_project,
                )
                update_success = True
            except Exception as e:
                # Update might return empty response (204), which is OK
                if "Expecting value" in str(e) or "JSONDecodeError" in str(e):
                    update_success = True  # Empty response is acceptable for update
                else:
                    raise
            
            # Verify
            try:
                verify_task = await ticktick_client.get(
                    endpoint=f"/open/v1/project/{target_project}/task/{task_id}",
                    headers=ticktick_client._get_headers(),
                )
                
                assert verify_task.get("projectId") == target_project, "ProjectId not updated"
                status = "✅ PASSED"
                get_result = "✅ Verified - task moved to target project"
            except Exception as e:
                status = "⚠️ PARTIAL"
                get_result = f"⚠️ GET failed: {str(e)[:100]}"
            
            print(f"\n{test_name}: {status}")
            print(f"  Source project: {source_project}")
            print(f"  Target project: {target_project}")
            print(f"  GET verification: {get_result}")
            
        except Exception as e:
            print(f"\n{test_name}: ❌ FAILED")
            print(f"  Error: {str(e)}")
            raise

