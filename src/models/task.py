"""
Task model
"""

from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict


class Task(BaseModel):
    """Task model"""
    
    model_config = ConfigDict(populate_by_name=True)
    
    id: Optional[str] = None
    title: str
    project_id: Optional[str] = Field(None, alias="projectId")
    column_id: Optional[str] = Field(None, alias="columnId")
    due_date: Optional[str] = Field(None, alias="dueDate")
    priority: int = 0  # 0: None, 1: Low, 2: Medium, 3: High
    status: int = 0  # 0: Incomplete, 1: Completed
    tags: List[str] = []
    notes: Optional[str] = Field(None, alias="content")
    created_time: Optional[str] = Field(None, alias="createdTime")
    modified_time: Optional[str] = Field(None, alias="modifiedTime")


class TaskCreate(BaseModel):
    """Task creation model"""
    
    model_config = ConfigDict(populate_by_name=True)
    
    title: str
    project_id: Optional[str] = Field(None, alias="projectId")
    due_date: Optional[str] = Field(None, alias="dueDate")
    priority: int = 0
    tags: List[str] = []
    notes: Optional[str] = None


class TaskUpdate(BaseModel):
    """Task update model"""
    
    model_config = ConfigDict(populate_by_name=True)
    
    title: Optional[str] = None
    project_id: Optional[str] = Field(None, alias="projectId")
    column_id: Optional[str] = Field(None, alias="columnId")
    due_date: Optional[str] = Field(None, alias="dueDate")
    priority: Optional[int] = None
    status: Optional[int] = None
    tags: Optional[List[str]] = None
    notes: Optional[str] = None
