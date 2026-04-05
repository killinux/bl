from pydantic import BaseModel, Field
from typing import Optional
from enum import Enum
import uuid
import time


class TaskType(str, Enum):
    screenshot = "screenshot"
    exec = "exec"
    logs = "logs"
    push_file = "push_file"


class TaskStatus(str, Enum):
    pending = "pending"
    in_progress = "in_progress"
    completed = "completed"
    failed = "failed"
    timeout = "timeout"


class TaskCreate(BaseModel):
    type: TaskType
    payload: dict = Field(default_factory=dict)


class Task(BaseModel):
    id: str = Field(default_factory=lambda: uuid.uuid4().hex[:12])
    type: TaskType
    payload: dict = Field(default_factory=dict)
    status: TaskStatus = TaskStatus.pending
    created_at: float = Field(default_factory=time.time)
    result: Optional[dict] = None
