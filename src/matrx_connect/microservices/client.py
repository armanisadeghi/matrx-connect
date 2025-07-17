import json
from typing import Dict, Any, Optional, AsyncGenerator

import httpx
from matrx_utils import vcprint

from ..socket.response.socket_printer import SocketPrinter
from ..socket.schema.processing.schema_processor import ValidationSystem
from ..exceptions.socket_errors import SocketSchemaError


class MicroserviceClient:
    def __init__(self, base_url, schema):
        self.base_url = base_url
        self.schema = schema

    @property
    def project_headers(self) -> Optional[Dict[str, str]]:
        return None

    async def _call(self, service_name: str, task_name: str, task_data: Dict[str, Any] = None,
                    validated: bool = True, headers: Optional[Dict[str, str]] = None,
                    stream_handler: SocketPrinter = None) -> AsyncGenerator[Dict[str, Any], None]:
        stream_handler = stream_handler or SocketPrinter("local_test_event")

        endpoint = f"/execute/{service_name}" if validated else f"/execute-direct/{service_name}"
        url = f"{self.base_url}{endpoint}"

        payload = {"taskName": task_name, "taskData": task_data or {}}
        request_headers = {"Content-Type": "application/json"}

        # Add project-level headers if they exist
        if self.project_headers:
            request_headers.update(self.project_headers)

        # Add call-specific headers
        if headers:
            request_headers.update(headers)

        final_responses = {
            "text": "",
            "data": [],
            "info": [],
            "error": [],
            "broker": [],
            "end": False
        }

        async with httpx.AsyncClient() as client:
            async with client.stream('POST', url, json=payload, headers=request_headers) as response:
                async for line in response.aiter_lines():
                    if line.startswith('data: '):
                        try:
                            event = json.loads(line[6:])
                            if "text" in event:
                                await stream_handler.send_chunk(event["text"])
                                final_responses["text"] += event["text"]
                            elif "data" in event:
                                await stream_handler.send_data(event["data"])
                                final_responses["data"].append(event["data"])
                            elif "error" in event:
                                await stream_handler.send_error(**event["error"])
                                final_responses["error"].append(event["error"])
                            elif "info" in event:
                                await stream_handler.send_status_update(**event["info"])
                                final_responses["info"].append(event["info"])
                            elif "end" in event:
                                await stream_handler.send_end()
                                final_responses["end"] = True
                                break
                        except json.JSONDecodeError:
                            continue

        yield final_responses

    async def api_call(self, service: str, task: str, task_data: dict):
        return await self.execute(service, task, task_data, stream_handler=None)

    async def api_call_default(self, task: str, task_data: dict):
        return await self.execute_default(task, task_data, stream_handler=None)

    async def execute_default(self, task: str, task_data: dict, stream_handler):
        return await self.execute("default_service", task, task_data, stream_handler)

    async def execute_direct_default(self, task: str, task_data: dict, stream_handler):
        return await self.execute_direct("default_service", task, task_data, stream_handler)

    async def execute(self, service: str, task: str, task_data: dict = None, stream_handler=None):
        async for result in self._call(service, task, task_data, validated=True, stream_handler=stream_handler):
            return result

    async def execute_direct(self, service: str, task: str, task_data: dict = None, stream_handler=None):
        async for result in self._call(service, task, task_data, validated=False, stream_handler=stream_handler):
            return result


class MicroserviceFactory:
    _instances: Dict[str, MicroserviceClient] = {}

    @staticmethod
    async def create_or_get_client_from_url(name, url=None):
        if name in MicroserviceFactory._instances:
            vcprint(
                f"Returning existing instance of {name} with endpoint {MicroserviceFactory._instances[name].base_url}",
                color="gold")
            return MicroserviceFactory._instances[name]

        if not url:
            raise ValueError("An endpoint is required for registering a microservice.")

        schema = await MicroserviceFactory._check_schema(url)
        MicroserviceFactory._instances[name] = MicroserviceClient(base_url=url, schema=schema)
        return MicroserviceFactory._instances[name]

    @staticmethod
    async def _check_schema(url):
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(f"{url}/schema")
                response.raise_for_status()
                schema = response.json()
                if not schema.get('response'):
                    raise RuntimeError("Given url is not a microservice.")
                if not schema['response'].get("definitions") or not schema['response'].get("tasks"):
                    raise RuntimeError("Given url is not a microservice.")
                ValidationSystem(schema['response'])
                return schema
            except httpx.HTTPStatusError as e:
                raise RuntimeError(f"HTTP error: {e.response.status_code} - {e.response.text}")
            except httpx.RequestError as e:
                raise RuntimeError(f"Connection error: {e}")
            except (SocketSchemaError, Exception) as e:
                raise
