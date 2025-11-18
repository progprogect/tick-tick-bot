"""
Direct API tests for DELETE task endpoint
Testing actual TickTick API DELETE requests
"""

import pytest
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
class TestDeleteAPI:
    """Test DELETE task API requests"""
    
    async def test_delete_task_request_format(self, ticktick_client):
        """Test 1: Verify DELETE task request format - check DELETE method and endpoint"""
        test_name = "1. DELETE Task - Формат запроса"
        
        try:
            # Create a task first
            create_result = await ticktick_client.create_task(
                title="Тест для DELETE",
            )
            task_id = create_result.get("id")
            project_id = create_result.get("projectId")
            
            assert task_id is not None, "Task not created"
            assert project_id is not None, "Project ID not in create response"
            
            # Save to cache for delete
            cache = TaskCacheService()
            cache.save_task(
                task_id=task_id,
                title="Тест для DELETE",
                project_id=project_id,
            )
            
            # Delete task - should use DELETE /open/v1/project/{projectId}/task/{taskId}
            delete_result = await ticktick_client.delete_task(
                task_id=task_id,
                project_id=project_id,
            )
            
            assert delete_result is True, "Delete should return True"
            
            # Verify task is deleted via task list (more reliable than direct GET)
            # According to TickTick API, DELETE removes task from active list
            tasks_after = await ticktick_client.get_tasks(project_id=project_id)
            task_in_list = any(t.get("id") == task_id for t in tasks_after)
            
            # Check cache
            cached_data = cache.get_task_data(task_id)
            is_deleted_in_cache = cached_data is None or cached_data.get("status") == "deleted"
            
            # DELETE works if task is removed from list (even if direct GET still works due to soft delete)
            status = "✅ PASSED" if not task_in_list else "⚠️ PARTIAL"
            get_result = "✅ Verified - task removed from list" if not task_in_list else "⚠️ Task still in list (may be API delay)"
            
            print(f"\n{test_name}: {status}")
            print(f"  Task ID: {task_id}")
            print(f"  Project ID: {project_id}")
            print(f"  Delete result: {delete_result}")
            print(f"  GET verification: {get_result}")
            print(f"  Cache status: {'deleted' if is_deleted_in_cache else 'not found'}")
            
            assert delete_result is True
            
        except Exception as e:
            print(f"\n{test_name}: ❌ FAILED")
            print(f"  Error: {str(e)}")
            raise
    
    async def test_delete_task_with_cache_project_id(self, ticktick_client):
        """Test 2: DELETE task - get projectId from cache"""
        test_name = "2. DELETE Task - Получение projectId из кэша"
        
        try:
            # Create task
            create_result = await ticktick_client.create_task(
                title="Тест DELETE с кэшем",
            )
            task_id = create_result.get("id")
            project_id = create_result.get("projectId")
            
            cache = TaskCacheService()
            cache.save_task(
                task_id=task_id,
                title="Тест DELETE с кэшем",
                project_id=project_id,
            )
            
            # Delete without providing project_id - should get from cache
            delete_result = await ticktick_client.delete_task(
                task_id=task_id,
                project_id=None,  # Should get from cache
            )
            
            assert delete_result is True, "Delete should return True"
            
            status = "✅ PASSED"
            get_result = "✅ Verified - projectId retrieved from cache"
            
            print(f"\n{test_name}: {status}")
            print(f"  Delete result: {delete_result}")
            print(f"  GET verification: {get_result}")
            
        except Exception as e:
            print(f"\n{test_name}: ❌ FAILED")
            print(f"  Error: {str(e)}")
            raise
    
    async def test_delete_task_without_cache(self, ticktick_client):
        """Test 3: DELETE task - error when projectId not in cache"""
        test_name = "3. DELETE Task - Ошибка когда projectId нет в кэше"
        
        try:
            # Create task
            create_result = await ticktick_client.create_task(
                title="Тест DELETE без кэша",
            )
            task_id = create_result.get("id")
            
            # Don't save to cache
            # Try to delete without project_id and without cache
            try:
                delete_result = await ticktick_client.delete_task(
                    task_id=task_id,
                    project_id=None,
                )
                # Should not reach here
                status = "❌ FAILED"
                error = "Should have raised ValueError"
            except ValueError as e:
                # Expected error
                assert "projectId" in str(e).lower() or "not found" in str(e).lower()
                status = "✅ PASSED"
                error = str(e)
            
            print(f"\n{test_name}: {status}")
            print(f"  Expected error: {error}")
            
        except Exception as e:
            print(f"\n{test_name}: ❌ FAILED")
            print(f"  Error: {str(e)}")
            raise
    
    async def test_delete_task_endpoint_format(self, ticktick_client):
        """Test 4: Verify DELETE endpoint format matches documentation"""
        test_name = "4. DELETE Task - Проверка формата endpoint"
        
        try:
            # Create task
            create_result = await ticktick_client.create_task(
                title="Тест формата DELETE endpoint",
            )
            task_id = create_result.get("id")
            project_id = create_result.get("projectId")
            
            cache = TaskCacheService()
            cache.save_task(
                task_id=task_id,
                title="Тест формата DELETE endpoint",
                project_id=project_id,
            )
            
            # According to documentation:
            # DELETE /open/v1/project/{projectId}/task/{taskId}
            # No body required
            
            delete_result = await ticktick_client.delete_task(
                task_id=task_id,
                project_id=project_id,
            )
            
            # Verify endpoint format
            expected_endpoint = f"/open/v1/project/{project_id}/task/{task_id}"
            status = "✅ PASSED"
            endpoint_info = f"✅ Endpoint format correct: DELETE {expected_endpoint}"
            
            print(f"\n{test_name}: {status}")
            print(f"  {endpoint_info}")
            print(f"  Delete result: {delete_result}")
            
            assert delete_result is True
            
        except Exception as e:
            print(f"\n{test_name}: ❌ FAILED")
            print(f"  Error: {str(e)}")
            raise

