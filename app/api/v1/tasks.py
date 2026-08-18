from fastapi import APIRouter, HTTPException
from celery.result import AsyncResult
from pydantic import BaseModel
from typing import Any

from app.worker import celery_app

router = APIRouter(prefix="/tasks", tags=["tasks"])


class TaskStatusResponse(BaseModel):
    task_id: str
    status: str
    result: Any | None = None


@router.get("/{task_id}", response_model=TaskStatusResponse)
async def get_task_status(task_id: str):
    """
    Retrieve the status of a background Celery task.
    """
    task = AsyncResult(task_id, app=celery_app)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    response = TaskStatusResponse(
        task_id=task_id,
        status=task.status
    )
    
    if task.status == "SUCCESS":
        response.result = task.result
    elif task.status == "FAILURE":
        response.result = str(task.info)

    return response
