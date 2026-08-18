import pytest
from unittest.mock import patch, MagicMock
from app.api.v1.tasks import TaskStatusResponse

@pytest.mark.asyncio
async def test_get_task_status_success(async_client):
    with patch("app.api.v1.tasks.AsyncResult") as mock_result:
        mock_task = MagicMock()
        mock_task.status = "SUCCESS"
        mock_task.result = {"report_id": "123"}
        mock_result.return_value = mock_task
        
        response = await async_client.get("/api/v1/tasks/test-task-123")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "SUCCESS"
        assert data["result"] == {"report_id": "123"}

@pytest.mark.asyncio
async def test_get_task_status_pending(async_client):
    with patch("app.api.v1.tasks.AsyncResult") as mock_result:
        mock_task = MagicMock()
        mock_task.status = "PENDING"
        mock_result.return_value = mock_task
        
        response = await async_client.get("/api/v1/tasks/test-task-456")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "PENDING"
        assert data["result"] is None
