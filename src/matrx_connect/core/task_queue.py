import asyncio
import threading
import time
import traceback
import warnings
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from typing import Callable, Optional

from matrx_utils import vcprint

# Ensure warnings are shown
warnings.filterwarnings("always")

LONG_RUNNING_SERVICES = {}

info = True
debug = False
verbose = False



@dataclass
class Task:
    service_name: Optional[str] = None
    user_id: str = "system"
    priority: int = 10
    data: Optional[dict] = None
    sid: Optional[str] = None
    namespace: Optional[str] = None
    stream_handler: Optional[Callable] = None
    is_sync: bool = False
    callback: Optional[Callable] = None

    def __post_init__(self):
        self.submit_time = getattr(self, "submit_time", time.time())

    def __lt__(self, other):
        return (self.priority, self.submit_time) < (other.priority, other.submit_time)


class TaskQueue:
    _instance = None
    _lock = threading.Lock()
    _worker_id_counter = 0  # For unique worker IDs

    @classmethod
    def get_instance(cls) -> "TaskQueue":
        vcprint("[TASK QUEUE] Getting instance", verbose=debug, color="yellow")
        return get_task_queue()

    @classmethod
    async def get_instance_async(cls) -> "TaskQueue":
        vcprint("[TASK QUEUE] Getting async instance", verbose=debug, color="yellow")
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, cls.get_instance)

    @classmethod
    def initialize(cls, user_sessions=None):
        from matrx_connect import get_user_session_namespace

        with cls._lock:
            if cls._instance is None:
                user_sessions = user_sessions or get_user_session_namespace()
                cls._instance = cls(user_sessions)
                loop = asyncio.get_event_loop()
                asyncio.create_task(cls._instance.start())
            return cls._instance

    @classmethod
    def reset(cls):
        vcprint("[TASK QUEUE] Resetting", verbose=info, color="yellow")
        with cls._lock:
            if cls._instance:
                asyncio.create_task(cls._instance.shutdown())
            cls._instance = None
            vcprint("[TASK QUEUE] Reset", verbose=info, color="yellow")
        return cls._instance

    def __init__(self, user_sessions):
        self.user_sessions = user_sessions
        self.queue = asyncio.PriorityQueue(maxsize=1000)
        self.background_queue = asyncio.PriorityQueue(maxsize=1000)
        self.user_tasks = Counter()
        self.user_limits = defaultdict(lambda: 5)
        self.system_service_factory = None
        self.short_running_workers = 50
        self.long_running_workers = 50
        self.running = True
        self.executor = ThreadPoolExecutor(max_workers=50)
        self._worker_ids = {}  # Track worker IDs
        self._user_task_queues = defaultdict(list)  # Track tasks per user

    def set_user_limit(self, user_id: str, limit: int):
        vcprint(f"[TASK QUEUE] Setting user limit for {user_id}: {limit}", verbose=info, color="yellow")
        self.user_limits[user_id] = max(0, limit)

    async def _cancel_user_tasks(self, user_id: str):
        vcprint(f"[TASK QUEUE] Cancelling all tasks for user {user_id}", verbose=info, color="yellow")
        tasks = self._user_task_queues.get(user_id, [])
        for task in tasks:
            if not task.done():
                task.cancel()
        self._user_task_queues[user_id].clear()
        self.user_tasks[user_id] = 0

    async def add_task(self, task: Task):
        if self.queue.full():
            vcprint(f"[TASK QUEUE] Queue full, rejecting task | Service: {task.service_name} | User: {task.user_id}", verbose=info, color="yellow")
            raise ValueError("Task queue full")
        if task.user_id != "system" and self.user_tasks[task.user_id] >= self.user_limits[task.user_id]:
            vcprint(f"[TASK QUEUE] User {task.user_id} exceeded task limit, cancelling all their tasks", verbose=info, color="yellow")
            await self._cancel_user_tasks(task.user_id)
            raise ValueError(f"User {task.user_id} exceeded task limit; all tasks cancelled")
        await self.queue.put(task)
        self.user_tasks[task.user_id] += 1
        self._user_task_queues[task.user_id].append(asyncio.current_task())
        vcprint(f"[TASK QUEUE] Task added | Service: {task.service_name} | User: {task.user_id} | Priority: {task.priority}", verbose=info, color="blue")

    def add_task_sync(self, task: Task):
        vcprint(f"[TASK QUEUE] Adding sync task | Service: {task.service_name} | User: {task.user_id}", verbose=info, color="yellow")
        loop = asyncio.get_event_loop()
        try:
            if loop.is_running():
                future = asyncio.run_coroutine_threadsafe(self.add_task(task), loop)
                future.result()
            else:
                asyncio.run(self.add_task(task))
        except Exception as e:
            vcprint(f"[TASK QUEUE] Error in add_task_sync: {str(e)}", verbose=True, color="red")
            traceback.print_exc()
            raise

    async def add_background_task(self, **kwargs):
        vcprint(f"[TASK QUEUE] Adding background task | kwargs: {kwargs}", verbose=info, color="yellow")
        if self.background_queue.full():
            vcprint(f"[TASK QUEUE] Background queue full, rejecting task | kwargs: {kwargs}", verbose=info, color="yellow")
            raise ValueError("Background queue full")
        task = Task(priority=100, **kwargs)
        if task.user_id != "system" and self.user_tasks[task.user_id] >= self.user_limits[task.user_id]:
            vcprint(f"[TASK QUEUE] User {task.user_id} exceeded task limit, cancelling all their tasks", verbose=info, color="yellow")
            await self._cancel_user_tasks(task.user_id)
            raise ValueError(f"User {task.user_id} exceeded task limit; all tasks cancelled")
        await self.background_queue.put(task)
        self.user_tasks[task.user_id] += 1
        self._user_task_queues[task.user_id].append(asyncio.current_task())
        vcprint(f"[TASK QUEUE] Background task added | Service: {task.service_name} | User: {task.user_id}", verbose=info, color="yellow")

    def add_background_task_sync(self, **kwargs):
        vcprint(f"[TASK QUEUE] Adding sync background task | kwargs: {kwargs}", verbose=info, color="yellow")
        loop = asyncio.get_event_loop()
        try:
            if loop.is_running():
                future = asyncio.run_coroutine_threadsafe(self.add_background_task(**kwargs), loop)
                future.result()
            else:
                asyncio.run(self.add_background_task(**kwargs))
        except Exception as e:
            vcprint(f"[TASK QUEUE] Error in add_background_task_sync: {str(e)}", verbose=True, color="red")
            traceback.print_exc()
            raise

    async def get_task(self) -> Optional[Task]:
        while self.running:
            try:
                task = await asyncio.wait_for(self.queue.get(), timeout=1.0)
                return task
            except asyncio.TimeoutError:
                try:
                    task = await asyncio.wait_for(self.background_queue.get(), timeout=1.0)
                    self.user_tasks[task.user_id] += 1
                    vcprint(f"[TASK QUEUE] Got background task | Service: {task.service_name} | User: {task.user_id}", verbose=info, color="yellow")
                    return task
                except asyncio.TimeoutError:
                    continue
            except Exception as e:
                vcprint(f"[TASK QUEUE] Error in get_task: {str(e)}", verbose=True, color="red")
                traceback.print_exc()
                raise
        vcprint("[TASK QUEUE] No task available, exiting get_task", verbose=info, color="yellow")
        return None

    async def complete_task(self, task: Task):
        vcprint(f"[TASK QUEUE] Completing task | Service: {task.service_name} | User: {task.user_id}", verbose=info, color="yellow")
        self.user_tasks[task.user_id] -= 1
        if self.user_tasks[task.user_id] <= 0:
            del self.user_tasks[task.user_id]
            self._user_task_queues[task.user_id].clear()
        vcprint(f"[TASK QUEUE] Task completed | Service: {task.service_name} | User: {task.user_id}", verbose=info, color="yellow")

    async def worker(self, worker_type: str):
        worker_id = f"{worker_type}-{self._worker_id_counter}"
        with self._lock:
            self._worker_id_counter += 1
            self._worker_ids[worker_id] = True
        loop = asyncio.get_running_loop()
        while self.running:
            task = await self.get_task()
            if not task:
                break
            vcprint(f"[TASK QUEUE] Worker busy | ID: {worker_id} | Service: {task.service_name} | User: {task.user_id} | Sync: {task.is_sync}", verbose=info, color="yellow")
            try:
                is_long_running = task.service_name in LONG_RUNNING_SERVICES if task.service_name else False
                if worker_type == "short" and is_long_running:
                    vcprint(f"[TASK QUEUE] Requeuing long task in short worker | ID: {worker_id} | Service: {task.service_name}", verbose=info, color="yellow")
                    await self.queue.put(task)
                    await asyncio.sleep(0.1)
                    self.user_tasks[task.user_id] -= 1
                    continue
                elif worker_type == "long" and not is_long_running and task.service_name:
                    vcprint(f"[TASK QUEUE] Requeuing short task in long worker | ID: {worker_id} | Service: {task.service_name}", verbose=info, color="yellow")
                    await self.queue.put(task)
                    await asyncio.sleep(0.1)
                    self.user_tasks[task.user_id] -= 1
                    continue
                try:
                    await asyncio.wait_for(self._process_task(task, loop), timeout=600)
                except asyncio.TimeoutError:
                    vcprint(f"[TASK QUEUE] Task timed out | ID: {worker_id} | Service: {task.service_name} | User: {task.user_id}", verbose=info, color="yellow")
                    traceback.print_exc()
                except Exception as e:
                    vcprint(f"[TASK QUEUE] Error in task execution | ID: {worker_id} | Service: {task.service_name} | User: {task.user_id} | Error: {str(e)}", verbose=info, color="yellow")
                    traceback.print_exc()
            except Exception as e:
                vcprint(f"[TASK QUEUE] Error processing task | ID: {worker_id} | Service: {task.service_name} | User: {task.user_id} | Error: {str(e)}", verbose=info, color="yellow")
                traceback.print_exc()
            finally:
                await self.complete_task(task)
                vcprint(f"[TASK QUEUE] Worker idle | ID: {worker_id}", verbose=info, color="yellow")
        vcprint(f"[TASK QUEUE] Worker stopped | ID: {worker_id}", verbose=info, color="yellow")
        with self._lock:
            del self._worker_ids[worker_id]

    async def _process_task(self, task: Task, loop: asyncio.AbstractEventLoop):
        vcprint(f"[TASK QUEUE] Starting task | Service: {task.service_name} | User: {task.user_id} | Sync: {task.is_sync}", verbose=info, color="yellow")
        try:
            if task.callback:
                if task.is_sync:

                    def sync_callback():
                        try:
                            return task.callback(task.data)
                        except Exception as e:
                            vcprint(f"[TASK QUEUE] Error in sync callback | Service: {task.service_name} | User: {task.user_id} | Error: {str(e)}", verbose=True, color="yellow")
                            traceback.print_exc()
                            return None

                    future = loop.run_in_executor(self.executor, sync_callback)
                    return await asyncio.wait_for(future, timeout=30)
                else:
                    try:
                        return await task.callback(task.data)
                    except Exception as e:
                        vcprint(f"[TASK QUEUE] Error in async callback | Service: {task.service_name} | User: {task.user_id} | Error: {str(e)}", verbose=True, color="yellow")
                        traceback.print_exc()
                        return None
            elif task.service_name:
                if task.sid:
                    try:
                        user_id, service_factory = await self.user_sessions.get_user_factory_and_id(task.sid)
                        if not service_factory:
                            vcprint(f"[TASK QUEUE] No ServiceFactory for SID {task.sid}", verbose=info, color="yellow")
                            return None

                        return await service_factory.process_request(sid=task.sid, user_id=user_id, data=task.data or {}, namespace=task.namespace or "/UserSession", service_name=task.service_name)
                    except Exception as e:
                        vcprint(f"[TASK QUEUE] Error processing SID task | Service: {task.service_name} | SID: {task.sid} | Error: {str(e)}", verbose=True, color="yellow")
                        traceback.print_exc()
                        return None
                else:
                    try:
                        if task.user_id != "system":
                            service_factory = self.user_sessions.user_service_factories.get(task.user_id)
                        else:
                            if not self.system_service_factory:
                                from common.socket.core.service_factory import ServiceFactory

                                self.system_service_factory = ServiceFactory()
                            service_factory = self.system_service_factory

                        if not service_factory:
                            vcprint(f"[TASK QUEUE] No ServiceFactory for user {task.user_id}", verbose=info, color="yellow")
                            return None

                        service = service_factory.create_service(task.service_name)
                        if hasattr(service, "stream_handler"):
                            service.stream_handler = task.stream_handler
                        if hasattr(service, "user_id"):
                            service.user_id = task.user_id

                        if task.is_sync:

                            def sync_process():
                                try:
                                    return service.process_task(task.data or {}, context={"namespace": task.namespace})
                                except Exception as e:
                                    vcprint(f"[TASK QUEUE] Error in sync service process | Service: {task.service_name} | User: {task.user_id} | Error: {str(e)}", verbose=True, color="yellow")
                                    traceback.print_exc()
                                    return None

                            future = loop.run_in_executor(self.executor, sync_process)
                            return await asyncio.wait_for(future, timeout=30)
                        else:
                            try:
                                return await service.process_task(task.data or {}, context={"namespace": task.namespace})
                            except Exception as e:
                                vcprint(f"[TASK QUEUE] Error in async service process | Service: {task.service_name} | User: {task.user_id} | Error: {str(e)}", verbose=True, color="yellow")
                                traceback.print_exc()
                                return None
                    except Exception as e:
                        vcprint(f"[TASK QUEUE] Error setting up service | Service: {task.service_name} | User: {task.user_id} | Error: {str(e)}", verbose=True, color="yellow")
                        traceback.print_exc()
                        return None
        except Exception as e:
            vcprint(f"[TASK QUEUE] Error in _process_task | Service: {task.service_name} | User: {task.user_id} | Error: {str(e)}", verbose=True, color="yellow")
            traceback.print_exc()
            return None

    async def start(self):
        short_tasks = []
        for i in range(self.short_running_workers):
            short_tasks.append(asyncio.create_task(self.worker("short")))
        long_tasks = []
        for i in range(self.long_running_workers):
            long_tasks.append(asyncio.create_task(self.worker("long")))
        self._worker_tasks = short_tasks + long_tasks

    async def shutdown(self):
        vcprint("[TASK QUEUE] Initiating shutdown", verbose=info, color="yellow")
        self.running = False
        if hasattr(self, "_worker_tasks"):
            for task in self._worker_tasks:
                task.cancel()
        self.executor.shutdown(wait=False)
        while not self.queue.empty():
            try:
                self.queue.get_nowait()
            except asyncio.QueueEmpty:
                break
        while not self.background_queue.empty():
            try:
                self.queue.get_nowait()
            except asyncio.QueueEmpty:
                break
        vcprint("[TASK QUEUE] Shutdown complete", verbose=info, color="yellow")


_task_queue_instance = None


def get_task_queue():
    global _task_queue_instance
    with threading.Lock():
        if _task_queue_instance is None:
            _task_queue_instance = TaskQueue.initialize()
        return _task_queue_instance
