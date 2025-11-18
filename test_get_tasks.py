"""
Test script to check what tasks are returned from TickTick API
"""
import asyncio
import json
from src.api.ticktick_client import TickTickClient
from src.config.settings import settings
from src.utils.logger import logger


async def test_get_tasks():
    """Test getting tasks from API"""
    client = TickTickClient()
    
    try:
        # Authenticate
        print("Authenticating...")
        auth_result = await client.authenticate()
        print(f"Authentication result: {auth_result}")
        
        # Get all projects
        print("\n=== Getting all projects ===")
        projects = await client.get_projects()
        print(f"Found {len(projects)} projects:")
        for p in projects:
            print(f"  - {p.get('name', 'N/A')} (ID: {p.get('id', 'N/A')})")
        
        # Get tasks from all projects
        print("\n=== Getting tasks from all projects ===")
        all_tasks = []
        
        for project in projects:
            project_id = project.get('id')
            project_name = project.get('name', 'N/A')
            
            if not project_id:
                continue
            
            print(f"\n--- Getting tasks from project: {project_name} ({project_id}) ---")
            try:
                response = await client.get(
                    endpoint=f"/open/v1/project/{project_id}/data",
                    headers=client._get_headers(),
                )
                
                print(f"Response type: {type(response)}")
                print(f"Response keys: {list(response.keys()) if isinstance(response, dict) else 'N/A'}")
                
                if isinstance(response, dict):
                    if "tasks" in response:
                        tasks = response["tasks"]
                        if isinstance(tasks, list):
                            print(f"Found {len(tasks)} tasks in this project")
                            all_tasks.extend(tasks)
                            
                            # Print all task titles
                            for task in tasks:
                                task_title = task.get('title', 'N/A')
                                task_id = task.get('id', 'N/A')
                                task_status = task.get('status', 'N/A')
                                print(f"  - '{task_title}' (id: {task_id}, status: {task_status})")
                    else:
                        print(f"No 'tasks' key in response. Full response: {json.dumps(response, ensure_ascii=False, indent=2)[:500]}")
                else:
                    print(f"Response is not a dict: {response}")
                    
            except Exception as e:
                print(f"Error getting tasks from project {project_name}: {e}")
                import traceback
                traceback.print_exc()
        
        # Summary
        print(f"\n=== SUMMARY ===")
        print(f"Total tasks found: {len(all_tasks)}")
        
        # Search for specific task
        search_title = "просто тестовая задача"
        print(f"\n=== Searching for task: '{search_title}' ===")
        
        # Normalize function
        def normalize_title(t: str) -> str:
            if not t:
                return ""
            import re
            return re.sub(r'\s+', ' ', t.lower().strip())
        
        search_normalized = normalize_title(search_title)
        print(f"Normalized search: '{search_normalized}'")
        
        # Try exact match
        exact_match = None
        for task in all_tasks:
            task_title = task.get('title', '')
            if normalize_title(task_title) == search_normalized:
                exact_match = task
                break
        
        if exact_match:
            print(f"✓ EXACT MATCH FOUND:")
            print(f"  Title: '{exact_match.get('title')}'")
            print(f"  ID: {exact_match.get('id')}")
            print(f"  Project ID: {exact_match.get('projectId')}")
            print(f"  Status: {exact_match.get('status')}")
        else:
            print(f"✗ Exact match NOT found")
            
            # Try partial match
            print(f"\nTrying partial match...")
            partial_matches = []
            for task in all_tasks:
                task_title = task.get('title', '')
                task_normalized = normalize_title(task_title)
                if (search_normalized in task_normalized or 
                    task_normalized in search_normalized):
                    partial_matches.append(task)
            
            if partial_matches:
                print(f"✓ Found {len(partial_matches)} partial matches:")
                for task in partial_matches:
                    print(f"  - '{task.get('title')}' (id: {task.get('id')}, status: {task.get('status')})")
            else:
                print(f"✗ No partial matches found")
                
                # Show all task titles for comparison
                print(f"\nAll task titles from API:")
                for i, task in enumerate(all_tasks, 1):
                    print(f"  {i}. '{task.get('title', 'N/A')}'")
        
        # Print all tasks as JSON for inspection
        print(f"\n=== All tasks as JSON (first 3) ===")
        for task in all_tasks[:3]:
            print(json.dumps(task, ensure_ascii=False, indent=2))
            
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_get_tasks())

