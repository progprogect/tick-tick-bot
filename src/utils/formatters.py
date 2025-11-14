"""
Message formatting utilities
"""

from typing import List, Dict, Any, Union
from datetime import datetime, timedelta, timezone
from src.models.task import Task
from src.config.constants import USER_TIMEZONE_OFFSET
from src.utils.date_utils import USER_TIMEZONE, get_current_datetime


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
        # Format date with time using format_datetime_for_user
        formatted_date = format_datetime_for_user(due_date)
        message += f" на {formatted_date}"
    
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
        # Format date with time using format_datetime_for_user
        due_date = task["dueDate"]
        if isinstance(due_date, str):
            formatted_date = format_datetime_for_user(due_date)
        else:
            formatted_date = format_datetime_for_user(str(due_date))
        changes.append(f"дата изменена на {formatted_date}")
    
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
    return f"✓ Задача '{title}' отмечена как выполненная"


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
        project: Project data
        
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


def format_date_for_user(date: Union[datetime, str]) -> str:
    """
    Format date for user-friendly display
    
    Converts datetime or ISO string to readable format:
    - "сегодня" for today
    - "завтра" for tomorrow
    - "послезавтра" for day after tomorrow
    - "DD.MM.YYYY" for other dates
    
    Args:
        date: datetime object or ISO 8601 string (with UTC+3 timezone)
        
    Returns:
        Formatted date string in Russian
    """
    # Convert to datetime if string
    if isinstance(date, str):
        try:
            # Handle ISO format with timezone
            date_str = date.replace('Z', '+00:00')
            dt = datetime.fromisoformat(date_str)
            # If timezone-naive, assume UTC+3
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=USER_TIMEZONE)
            else:
                # Convert to UTC+3
                dt = dt.astimezone(USER_TIMEZONE)
        except (ValueError, AttributeError):
            # If parsing fails, return as is
            return date
    else:
        # datetime object
        dt = date
        # Ensure timezone-aware
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=USER_TIMEZONE)
        else:
            # Convert to UTC+3
            dt = dt.astimezone(USER_TIMEZONE)
    
    # Get today in UTC+3
    today = get_current_datetime().date()
    date_only = dt.date()
    
    # Calculate difference
    delta = (date_only - today).days
    
    if delta == 0:
        return "сегодня"
    elif delta == 1:
        return "завтра"
    elif delta == 2:
        return "послезавтра"
    else:
        # Format as DD.MM.YYYY
        return date_only.strftime('%d.%m.%Y')


def format_datetime_for_user(datetime_str: str) -> str:
    """
    Format datetime with time for user-friendly display
    
    Converts ISO datetime string to readable format:
    - "сегодня в 10:00" for today with time
    - "завтра в 10:00" for tomorrow with time
    - "14.11.2025 в 10:00" for other dates with time
    - "сегодня" for today at midnight (00:00:00)
    - "завтра" for tomorrow at midnight (00:00:00)
    
    Args:
        datetime_str: ISO 8601 datetime string (with UTC+3 timezone)
        
    Returns:
        Formatted datetime string in Russian
    """
    try:
        # Handle ISO format with timezone
        date_str = datetime_str.replace('Z', '+00:00')
        dt = datetime.fromisoformat(date_str)
        
        # If timezone-naive, assume UTC+3
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=USER_TIMEZONE)
        else:
            # Convert to UTC+3
            dt = dt.astimezone(USER_TIMEZONE)
    except (ValueError, AttributeError):
        # If parsing fails, try format_date_for_user as fallback
        return format_date_for_user(datetime_str)
    
    # Get today in UTC+3
    today = get_current_datetime().date()
    date_only = dt.date()
    time_only = dt.time()
    
    # Check if time is midnight (00:00:00)
    is_midnight = time_only.hour == 0 and time_only.minute == 0 and time_only.second == 0
    
    # Calculate difference
    delta = (date_only - today).days
    
    # Format date part
    if delta == 0:
        date_part = "сегодня"
    elif delta == 1:
        date_part = "завтра"
    elif delta == 2:
        date_part = "послезавтра"
    else:
        date_part = date_only.strftime('%d.%m.%Y')
    
    # Add time part if not midnight
    if is_midnight:
        return date_part
    else:
        time_str = time_only.strftime('%H:%M')
        return f"{date_part} в {time_str}"

