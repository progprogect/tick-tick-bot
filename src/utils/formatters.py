"""
Message formatting utilities
"""

from typing import List, Dict, Any
from datetime import datetime
from src.models.task import Task


def format_task_created(task: Dict[str, Any]) -> str:
    """
    Format task creation confirmation message
    
    Args:
        task: Task data
        
    Returns:
        Formatted message
    """
    title = task.get("title", "Задача")
    project_id = task.get("projectId", "Inbox")
    due_date = task.get("dueDate")
    
    message = f"✓ Задача '{title}' создана"
    
    if project_id and project_id != "Inbox":
        message += f" в списке {project_id}"
    
    if due_date:
        message += f" на {due_date}"
    
    return message


def format_task_updated(task: Dict[str, Any]) -> str:
    """
    Format task update confirmation message
    
    Args:
        task: Task data with updated fields (should contain only changed fields)
        
    Returns:
        Formatted message
    """
    title = task.get("title", "Задача")
    changes = []
    
    # Check for changed fields (only show what was actually updated)
    if "dueDate" in task and task["dueDate"]:
        # Format date nicely
        due_date = task["dueDate"]
        if isinstance(due_date, str):
            # Try to format ISO date
            try:
                from datetime import datetime
                dt = datetime.fromisoformat(due_date.replace('Z', '+00:00'))
                due_date = dt.strftime('%d.%m.%Y')
            except:
                pass
        changes.append(f"дата изменена на {due_date}")
    
    if "title" in task and task.get("title") != title:
        changes.append(f"название изменено на '{task['title']}'")
    
    if "priority" in task and task["priority"] is not None:
        priority_names = {0: "обычный", 1: "низкий", 2: "средний", 3: "высокий"}
        priority_text = priority_names.get(task["priority"], f"приоритет {task['priority']}")
        changes.append(f"приоритет изменен на {priority_text}")
    
    if "tags" in task and task["tags"]:
        changes.append(f"теги добавлены: {', '.join(task['tags'])}")
    
    if "content" in task and task["content"]:
        changes.append("заметка добавлена")
    
    if "status" in task and task["status"] is not None:
        status_text = "выполнена" if task["status"] == 1 else "не выполнена"
        changes.append(f"статус изменен на {status_text}")
    
    if "projectId" in task and task["projectId"]:
        changes.append(f"список изменен на {task['projectId']}")
    
    if changes:
        message = f"✓ Задача '{title}' обновлена: {', '.join(changes)}"
    else:
        message = f"✓ Задача '{title}' обновлена"
    
    return message


def format_task_deleted(title: str) -> str:
    """
    Format task deletion confirmation message
    
    Args:
        title: Task title
        
    Returns:
        Formatted message
    """
    return f"✓ Задача '{title}' удалена"


def format_task_completed(title: str) -> str:
    """
    Format task completion confirmation message
    
    Args:
        title: Task title
        
    Returns:
        Formatted message
    """
    return f"✓ Задача '{title}' выполнена"


def format_bulk_operation(operation: str, count: int) -> str:
    """
    Format bulk operation confirmation message
    
    Args:
        operation: Operation name
        count: Number of items processed
        
    Returns:
        Formatted message
    """
    return f"✓ {operation}: обработано {count} задач"


def format_analytics(analytics: Dict[str, Any]) -> str:
    """
    Format analytics data message
    
    Args:
        analytics: Analytics data
        
    Returns:
        Formatted message
    """
    period = analytics.get("period", "период")
    work_time = analytics.get("work_time", 0)
    personal_time = analytics.get("personal_time", 0)
    total_time = analytics.get("total_time", 0)
    
    message = f"📊 Аналитика за {period}:\n\n"
    
    if work_time > 0:
        message += f"Рабочее время: {work_time} часов\n"
    
    if personal_time > 0:
        message += f"Личное время: {personal_time} часов\n"
    
    if total_time > 0:
        message += f"Общее время: {total_time} часов"
    
    return message


def format_project_created(project: Dict[str, Any]) -> str:
    """
    Format project creation confirmation message
    
    Args:
        project: Project data dictionary
        
    Returns:
        Formatted message
    """
    name = project.get("name", "Проект")
    project_id = project.get("id", "")
    
    message = f"✓ Проект '{name}' создан"
    
    if project_id:
        message += f" (ID: {project_id})"
    
    return message


def format_project_deleted(project_name: str) -> str:
    """
    Format project deletion confirmation message
    
    Args:
        project_name: Project name
        
    Returns:
        Formatted message
    """
    return f"✓ Проект '{project_name}' удален"

