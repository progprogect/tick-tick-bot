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
    tags = task.get("tags", [])
    notes = task.get("content") or task.get("notes")
    priority = task.get("priority", 0)
    
    # Get project name if possible
    project_name = None
    if project_id and not project_id.startswith("inbox"):
        # Try to get project name from cache
        try:
            from src.services.project_cache_service import ProjectCacheService
            from src.api.ticktick_client import TickTickClient
            # This is a bit hacky, but we need client instance
            # For now, just show project_id
            project_name = None
        except:
            pass
    
    message = f"✓ Задача '{title}' создана"
    
    # Add project info
    if project_id:
        if project_id.startswith("inbox"):
            message += " в Inbox"
        elif project_name:
            message += f" в списке '{project_name}'"
        else:
            message += f" (ID проекта: {project_id[:8]}...)"
    
    # Add due date
    if due_date:
        try:
            from datetime import datetime
            dt = datetime.fromisoformat(due_date.replace('Z', '+00:00'))
            formatted_date = dt.strftime('%d.%m.%Y')
            message += f"\n📅 Срок выполнения: {formatted_date}"
        except:
            message += f"\n📅 Срок выполнения: {due_date}"
    
    # Add priority
    if priority and priority > 0:
        priority_names = {1: "низкий", 3: "средний", 5: "высокий"}
        priority_text = priority_names.get(priority, f"приоритет {priority}")
        message += f"\n⚡ Приоритет: {priority_text}"
    
    # Add tags
    if tags:
        tags_list = ', '.join(tags)
        message += f"\n🏷️ Теги: {tags_list}"
    
    # Add notes preview
    if notes:
        notes_preview = notes[:50] + "..." if len(notes) > 50 else notes
        message += f"\n📝 Заметка: {notes_preview}"
    
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
    details = []
    
    # Check for changed fields (only show what was actually updated)
    if "dueDate" in task and task["dueDate"]:
        # Format date nicely
        due_date = task["dueDate"]
        formatted_date = due_date
        if isinstance(due_date, str):
            # Try to format ISO date
            try:
                from datetime import datetime
                dt = datetime.fromisoformat(due_date.replace('Z', '+00:00'))
                formatted_date = dt.strftime('%d.%m.%Y')
            except:
                pass
        changes.append("дата выполнения")
        details.append(f"📅 Новая дата: {formatted_date}")
    
    if "title" in task and task.get("title") != title:
        changes.append("название")
        details.append(f"📝 Новое название: '{task['title']}'")
    
    if "priority" in task and task["priority"] is not None:
        priority_names = {0: "обычный", 1: "низкий", 3: "средний", 5: "высокий"}
        priority_text = priority_names.get(task["priority"], f"приоритет {task['priority']}")
        changes.append("приоритет")
        details.append(f"⚡ Новый приоритет: {priority_text}")
    
    if "tags" in task and task["tags"]:
        changes.append("теги")
        tags_list = ', '.join(task["tags"])
        details.append(f"🏷️ Теги: {tags_list}")
    
    if "content" in task and task["content"]:
        changes.append("заметка")
        content_preview = task["content"][:50] + "..." if len(task["content"]) > 50 else task["content"]
        details.append(f"📝 Заметка: {content_preview}")
    
    if "status" in task and task["status"] is not None:
        status_text = "выполнена" if task["status"] == 2 else "не выполнена"
        changes.append("статус")
        details.append(f"✓ Статус: {status_text}")
    
    if "projectId" in task and task["projectId"]:
        changes.append("список")
        project_id = task["projectId"]
        if project_id.startswith("inbox"):
            details.append(f"📁 Новый список: Inbox")
        else:
            details.append(f"📁 Новый список: {project_id[:8]}...")
    
    if changes:
        message = f"✓ Задача '{title}' обновлена\n\n"
        message += "Изменения:\n"
        message += "\n".join(f"  • {detail}" for detail in details)
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
    return f"✓ Задача '{title}' удалена\n\n🗑️ Задача была полностью удалена из TickTick"


def format_task_completed(title: str) -> str:
    """
    Format task completion confirmation message
    
    Args:
        title: Task title
        
    Returns:
        Formatted message
    """
    return f"✓ Задача '{title}' выполнена\n\n✅ Задача отмечена как выполненная"


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


def format_date_for_user(date: datetime) -> str:
    """
    Format datetime object for user-friendly display
    
    Args:
        date: Datetime object (timezone-aware or naive)
        
    Returns:
        Formatted date string (e.g., "25.11.2025")
    """
    try:
        # If timezone-aware, convert to local timezone for display
        if date.tzinfo is not None:
            # Use the date as-is, just format it
            return date.strftime('%d.%m.%Y')
        else:
            # Naive datetime, format as-is
            return date.strftime('%d.%m.%Y')
    except Exception:
        # Fallback: try to convert to string
        return str(date.date() if hasattr(date, 'date') else date)

