import logging
import time
from contextlib import asynccontextmanager, AsyncExitStack
from typing import Callable
from typing import Dict, Any, Optional

from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from matrx_utils import vcprint, settings
from pydantic import BaseModel

from ..socket.schema import get_runtime_schema
from ..mcp_server.http_server import mcp as mcp_bridge
from matrx_connect import get_task_queue
from .http_executor import HTTPExecutor

logger = logging.getLogger('app')
_fast_api_app = None


def create_app(app_name, app_description, app_version, startup: Callable = None, shutdown: Callable = None) -> FastAPI:
    """Create and configure the FastAPI application"""

    @asynccontextmanager
    async def app_lifespan(app: FastAPI):

        task_queue = get_task_queue()
        logger.info("[Matrx Connect] Task Queue Initialized.")
        vcprint("[Matrx Connect] All Core Services Starting...", color="green")

        if startup:
            try:
                startup()
            except Exception as e:
                vcprint(e, "Startup method failed", color="red")
                logger.error("Startup method failed.")

        yield

        logger.info("Shutting down gracefully...")
        logger.info("Task Queue Shutdown complete.")
        await task_queue.shutdown()
        if shutdown:
            try:
                shutdown()
            except Exception as e:
                vcprint(e, "Shutdown method failed", color="red")
                logger.error("Shutdown method failed.")

    @asynccontextmanager
    async def combined_lifespan(app: FastAPI):
        async with AsyncExitStack() as stack:
            await stack.enter_async_context(app_lifespan(app))
            await stack.enter_async_context(mcp_bridge.session_manager.run())
            yield

    main_app = FastAPI(
        title=app_name,
        version=app_version,
        description=app_description,
        docs_url=None,
        redoc_url=None,
        lifespan=combined_lifespan
    )

    main_app.mount(path="/mcp-server", app=mcp_bridge.streamable_http_app())

    @main_app.get("/", include_in_schema=False)
    async def root():
        return {
            "message": f"Welcome to {app_name} API",
            "version": app_version,
            "mcp": "/mcp-server/mcp",
            "schema": "/schema"
        }

    @main_app.middleware("http")
    async def log_requests(request, call_next):
        logger = logging.getLogger("app")
        start_time = time.time()
        path = request.url.path
        method = request.method

        logger.info(f"Request started: {method} {path}")

        try:
            response = await call_next(request)
            process_time = (time.time() - start_time) * 1000
            status_code = response.status_code

            logger.info(f"Request completed: {method} {path} - Status: {status_code} - Time: {process_time:.2f}ms")
            response.headers["X-Process-Time"] = f"{process_time:.2f}ms"
            return response
        except Exception as e:
            logger.error(f"Request failed: {method} {path} - Error: {str(e)}", exc_info=True)
            raise

    return main_app


def get_app(app_name=None, app_description=None, app_version=None, startup: Callable = None, shutdown: Callable = None):
    global _fast_api_app
    if not _fast_api_app:
        _fast_api_app = create_app(app_name=app_name, app_description=app_description, app_version=app_version,
                                   startup=startup, shutdown=shutdown)
        return _fast_api_app

    return _fast_api_app


app = get_app(settings.APP_NAME, settings.APP_DESCRIPTION, settings.APP_VERSION)


class TaskPayload(BaseModel):
    taskName: str
    taskData: Optional[Dict[str, Any]] = {}


@app.post("/execute-direct/{service_name}")
async def execute_direct(
        service_name: str,
        payload: TaskPayload,
):
    """
    Direct execution bypassing schema validation.
    Updates taskData directly as service instance attributes.

    Response streams in real-time with same format as socket responses.
    """
    headers = {
        "Content-Type": "text/event-stream",
        "Cache-Control": "no-cache",
        "Connection": "keep-alive",
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Headers": "Cache-Control",
    }
    http_executor = HTTPExecutor()
    return StreamingResponse(
        http_executor.execute_direct(
            service_name=service_name,
            task_name=payload.taskName,
            task_data=payload.taskData or {}
        ),
        media_type="text/event-stream",
        headers=headers
    )


@app.post("/execute/{service_name}")
async def execute_validated(
        service_name: str,
        payload: TaskPayload,
):
    headers = {
        "Content-Type": "text/event-stream",
        "Cache-Control": "no-cache",
        "Connection": "keep-alive",
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Headers": "Cache-Control",
    }
    http_executor = HTTPExecutor()

    return StreamingResponse(
        http_executor.execute_validated(
            service_name=service_name,
            task_name=payload.taskName,
            task_data=payload.taskData or {}
        ),
        media_type="text/event-stream",
        headers=headers
    )


@app.get("/schema")
async def app_schema():
    try:
        schema = get_runtime_schema()
        return {
            "success": True,
            "message": None,
            "response": schema
        }
    except Exception as e:
        return {
            "success": False,
            "message": f"Runtime error occurred: {e}",
            "response": None
        }
