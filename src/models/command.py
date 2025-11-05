"""
Command model for parsing user commands
"""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, ConfigDict
from enum import Enum


class ActionType(str, Enum):
    """Action types for commands"""
    CREATE_TASK = "create_task"
    UPDATE_TASK = "update_task"
    DELETE_TASK = "delete_task"
    MOVE_TASK = "move_task"
    ADD_TAGS = "add_tags"
    ADD_NOTE = "add_note"
    CREATE_RECURRING_TASK = "create_recurring_task"
    SET_REMINDER = "set_reminder"
    GET_ANALYTICS = "get_analytics"
    OPTIMIZE_SCHEDULE = "optimize_schedule"
    BULK_MOVE = "bulk_move"
    BULK_ADD_TAGS = "bulk_add_tags"
    LIST_TASKS = "list_tasks"  # Просмотр задач


class FieldModifier(str, Enum):
    """Modifier types for field operations"""
    REPLACE = "replace"  # Заменить полностью
    MERGE = "merge"      # Объединить (теги)
    APPEND = "append"    # Добавить к концу (заметки)
    REMOVE = "remove"    # Удалить (теги)


class Recurrence(BaseModel):
    """Recurrence model for recurring tasks"""
    type: str  # "daily", "weekly", "monthly"
    interval: int = 1  # Every N days/weeks/months


class TaskIdentifier(BaseModel):
    """Task identifier for finding tasks"""
    type: str  # "title", "id", "context"
    value: str


class FieldModification(BaseModel):
    """Field modification with context"""
    value: Any
    modifier: FieldModifier = FieldModifier.REPLACE
    metadata: Dict[str, Any] = Field(default_factory=dict)


class Operation(BaseModel):
    """One operation in composite command"""
    type: ActionType
    requires_current_data: bool = False  # Need current task data?
    task_identifier: Optional[TaskIdentifier] = None
    params: Dict[str, Any] = Field(default_factory=dict)
    modifications: Optional[Dict[str, FieldModification]] = None  # For update_task
    depends_on: Optional[str] = None  # ID of previous operation (for chains)


class ParsedCommand(BaseModel):
    """Parsed command from GPT - supports both old and new formats"""
    
    model_config = ConfigDict(populate_by_name=True, use_enum_values=True)
    
    # New format: composite commands
    operations: Optional[List[Operation]] = None
    task_identifier: Optional[TaskIdentifier] = None  # Common identifier for all operations
    
    # Old format: single action (for backward compatibility)
    action: Optional[ActionType] = None
    title: Optional[str] = None
    task_id: Optional[str] = Field(None, alias="taskId")
    project_id: Optional[str] = Field(None, alias="projectId")
    target_project_id: Optional[str] = Field(None, alias="targetProjectId")
    due_date: Optional[str] = Field(None, alias="dueDate")
    priority: Optional[int] = None
    tags: Optional[List[str]] = None
    notes: Optional[str] = None
    recurrence: Optional[Recurrence] = None
    reminder: Optional[str] = None
    period: Optional[str] = None  # For analytics: "week", "month", etc.
    start_date: Optional[str] = Field(None, alias="startDate")  # For filtering tasks
    end_date: Optional[str] = Field(None, alias="endDate")  # For filtering tasks
    query_type: Optional[str] = Field(None, alias="queryType")  # For context: "last_created", "first_created", "all"
    limit: Optional[int] = None  # Limit number of tasks to show
    sort_by: Optional[str] = Field(None, alias="sortBy")  # "createdTime", "dueDate", etc.
    error: Optional[str] = None
    
    def is_composite(self) -> bool:
        """Check if command uses new composite format"""
        return self.operations is not None and len(self.operations) > 0

