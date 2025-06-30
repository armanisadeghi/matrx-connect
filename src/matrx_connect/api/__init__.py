import logging
import time
from contextlib import asynccontextmanager
from typing import List
from fastapi import FastAPI
from matrx_utils import vcprint
from matrx_connect import get_task_queue
from typing import Callable

logger = logging.getLogger('app')


def create_app(app_name, app_description, app_version, startup: Callable=None, shutdown: Callable =None, mount_apps: List[tuple[str, FastAPI]]= None) -> FastAPI:
    """Create and configure the FastAPI application"""

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        
        
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

            

    main_app = FastAPI(
        title=app_name,
        version=app_version,
        description=app_description,
        docs_url=None,
        redoc_url=None,
        lifespan=lifespan
    )

    if mount_apps:
        for path, app in mount_apps:
            main_app.mount(path, app)


    @main_app.get("/", include_in_schema=False)
    async def root():
        return {
            "message": f"Welcome to {app_name} API",
            "version": app_version,
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