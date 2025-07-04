from typing import Dict, Any, Optional

from pydantic import BaseModel
from matrx_utils import settings
from ..api import get_app
from .api_executor import execute


app = get_app(settings.APP_NAME, settings.APP_DESCRIPTION, settings.APP_VERSION)


class TaskPayload(BaseModel):
    taskName: str
    taskData: Optional[Dict[str, Any]] = {}


@app.post("/execute_task/{service_name}")
async def dynamic_endpoint(
        service_name: str,
        payload: TaskPayload
):

    task_data = {"taskName": payload.taskName, "taskData": payload.taskData}

    return await execute(service_name, task_data)
