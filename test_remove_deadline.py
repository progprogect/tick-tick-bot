#!/usr/bin/env python3
"""
Test script to check deadline removal via TickTick API
"""
import asyncio
import httpx
import json
import os
from datetime import datetime, timedelta

# Get access token from environment or use hardcoded for testing
ACCESS_TOKEN = os.getenv("TICKTICK_ACCESS_TOKEN", "tp_129f30f9ec524ded813233f2e4b94083")
BASE_URL = "https://api.ticktick.com"
API_VERSION = "v1"


async def test_remove_deadline():
    """Test creating task with deadline and removing it"""
    headers = {"Authorization": f"Bearer {ACCESS_TOKEN}"}
    
    async with httpx.AsyncClient() as client:
        try:
            # Step 1: Create a test task with deadline
            tomorrow = datetime.now() + timedelta(days=1)
            due_date_iso = tomorrow.strftime('%Y-%m-%dT%H:%M:%S+03:00')
            print(f"\n📅 Creating task with deadline: {due_date_iso}")
            
            create_data = {
                "title": "Тест удаления дедлайна",
                "projectId": "inbox",
                "dueDate": due_date_iso
            }
            
            response = await client.post(
                f"{BASE_URL}/open/{API_VERSION}/task",
                headers=headers,
                json=create_data
            )
            
            if response.status_code not in [200, 201]:
                print(f"❌ Failed to create task: {response.status_code} - {response.text}")
                return
            
            task_data = response.json()
            task_id = task_data.get("id")
            created_due_date = task_data.get("dueDate")
            print(f"✓ Task created: {task_id}")
            print(f"  Due date: {created_due_date}")
            
            if not task_id:
                print("❌ Failed to get task ID")
                return
            
            await asyncio.sleep(2)
            
            # Step 2: Try different methods to remove deadline
            print("\n🧪 Testing deadline removal methods...")
            
            # Method 1: Set dueDate to null
            print("\n1. Trying dueDate: null")
            try:
                update_data_1 = {
                    "id": task_id,
                    "projectId": "inbox",
                    "dueDate": None
                }
                response_1 = await client.post(
                    f"{BASE_URL}/open/{API_VERSION}/task/{task_id}",
                    headers=headers,
                    json=update_data_1
                )
                print(f"   Status: {response_1.status_code}")
                print(f"   Response: {response_1.text[:200]}")
                
                # Check if deadline was removed
                await asyncio.sleep(1)
                get_response = await client.get(
                    f"{BASE_URL}/open/{API_VERSION}/task/{task_id}",
                    headers=headers
                )
                if get_response.status_code == 200:
                    updated_task = get_response.json()
                    updated_due_date = updated_task.get("dueDate")
                    print(f"   Updated dueDate: {updated_due_date}")
                    if not updated_due_date:
                        print("   ✓ Deadline removed successfully with null!")
                        method_worked = True
                    else:
                        print("   ❌ Deadline still present")
                        method_worked = False
                else:
                    print(f"   ❌ Failed to get task: {get_response.status_code}")
                    method_worked = False
                    updated_due_date = created_due_date
            except Exception as e:
                print(f"   ❌ Error: {e}")
                method_worked = False
                updated_due_date = created_due_date
            
            # If method 1 didn't work, try method 2: empty string
            if not method_worked and updated_due_date:
                print("\n2. Trying dueDate: empty string")
                try:
                    update_data_2 = {
                        "id": task_id,
                        "projectId": "inbox",
                        "dueDate": ""
                    }
                    response_2 = await client.post(
                        f"{BASE_URL}/open/{API_VERSION}/task/{task_id}",
                        headers=headers,
                        json=update_data_2
                    )
                    print(f"   Status: {response_2.status_code}")
                    print(f"   Response: {response_2.text[:200]}")
                    
                    await asyncio.sleep(1)
                    get_response = await client.get(
                        f"{BASE_URL}/open/{API_VERSION}/task/{task_id}",
                        headers=headers
                    )
                    if get_response.status_code == 200:
                        updated_task = get_response.json()
                        updated_due_date = updated_task.get("dueDate")
                        print(f"   Updated dueDate: {updated_due_date}")
                        if not updated_due_date:
                            print("   ✓ Deadline removed successfully with empty string!")
                            method_worked = True
                        else:
                            print("   ❌ Deadline still present")
                            method_worked = False
                except Exception as e:
                    print(f"   ❌ Error: {e}")
                    method_worked = False
            
            # If method 2 didn't work, try method 3: omit the field
            if not method_worked and updated_due_date:
                print("\n3. Trying to set deadline again, then remove...")
                try:
                    # Set deadline again first
                    tomorrow_again = datetime.now() + timedelta(days=2)
                    due_date_iso_again = tomorrow_again.strftime('%Y-%m-%dT%H:%M:%S+03:00')
                    
                    set_response = await client.post(
                        f"{BASE_URL}/open/{API_VERSION}/task/{task_id}",
                        headers=headers,
                        json={
                            "id": task_id,
                            "projectId": "inbox",
                            "dueDate": due_date_iso_again
                        }
                    )
                    print(f"   Set deadline again: {set_response.status_code}")
                    await asyncio.sleep(1)
                    
                    # Now try removing with null
                    update_data_3 = {
                        "id": task_id,
                        "projectId": "inbox",
                        "dueDate": None
                    }
                    response_3 = await client.post(
                        f"{BASE_URL}/open/{API_VERSION}/task/{task_id}",
                        headers=headers,
                        json=update_data_3
                    )
                    print(f"   Status: {response_3.status_code}")
                    print(f"   Response: {response_3.text[:200]}")
                    
                    await asyncio.sleep(1)
                    get_response = await client.get(
                        f"{BASE_URL}/open/{API_VERSION}/task/{task_id}",
                        headers=headers
                    )
                    if get_response.status_code == 200:
                        updated_task = get_response.json()
                        updated_due_date = updated_task.get("dueDate")
                        print(f"   Updated dueDate: {updated_due_date}")
                        if not updated_due_date:
                            print("   ✓ Deadline removed successfully!")
                            method_worked = True
                        else:
                            print("   ❌ Deadline still present")
                except Exception as e:
                    print(f"   ❌ Error: {e}")
            
            # Summary
            print("\n" + "="*50)
            if method_worked:
                print("✓ SUCCESS: Found working method to remove deadline!")
            else:
                print("❌ FAILED: Could not remove deadline with tested methods")
            print("="*50)
            
            # Cleanup: Delete test task
            print(f"\n🧹 Cleaning up: deleting test task {task_id}")
            try:
                delete_response = await client.delete(
                    f"{BASE_URL}/open/{API_VERSION}/project/inbox/task/{task_id}",
                    headers=headers
                )
                if delete_response.status_code in [200, 204]:
                    print("✓ Test task deleted")
                else:
                    print(f"⚠️  Failed to delete test task: {delete_response.status_code} - {delete_response.text}")
            except Exception as e:
                print(f"⚠️  Failed to delete test task: {e}")
        
        except Exception as e:
            print(f"❌ Test failed: {e}")
            import traceback
            traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_remove_deadline())
