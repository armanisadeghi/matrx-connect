import json
import asyncio
from typing import Any, Dict, List, Optional, AsyncGenerator
from datetime import datetime
import uuid
import enum
import dataclasses
from ..socket.response.response_types import BrokerResponse


class HTTPStreamHandler:
    """
    HTTP streaming handler that implements the exact same interface as SocketEmitter
    but streams via HTTP Server-Sent Events. NO accumulation logic.
    """

    def __init__(self, event_name: str, request_id: str = None):
        self.event_name = event_name
        self.request_id = request_id or str(uuid.uuid4())
        self._stream_queue = asyncio.Queue()
        self._ended = False

    async def _emit_http(self, response_type: str, data: Any = None):
        """Emit HTTP response in the same format as socket responses"""
        if self._ended:
            return
        if response_type == "chunk":
            response_data = {"text": data}
        elif response_type == "data":
            response_data = {"data": self._serialize(data)}
        elif response_type == "info":
            response_data = {"info": data}
        elif response_type == "error":
            response_data = {"error": data}
        elif response_type == "broker":
            response_data = {"broker": data}
        elif response_type == "end":
            response_data = {"end": True}
        else:
            response_data = data

        sse_message = f"data: {json.dumps(response_data)}\n\n"
        await self._stream_queue.put(sse_message)

    async def send_chunk(self, chunk: str):
        """Send text chunk - matches SocketEmitter interface"""
        await self._emit_http("chunk", chunk)

    async def send_chunk_final(self, chunk: str):
        """Send final text chunk and end"""
        await self.send_chunk(chunk)
        await self.send_end()

    async def send_data(self, data: Any):
        """Send data object - matches SocketEmitter interface"""
        if not isinstance(data, dict):
            await self._emit_http("data", data)
            return

        # Handle nested data like SocketEmitter
        if "data" in data:
            nested = data.pop("data")
            if isinstance(nested, dict):
                data.update(nested)
            else:
                data = nested

        await self._emit_http("data", data)

    async def send_data_final(self, data: Any):
        """Send final data and end"""
        await self.send_data(data)
        await self.send_end()

    async def send_status_update(
            self,
            status: str,
            system_message: Optional[str] = None,
            user_visible_message: Optional[str] = None,
            metadata: Optional[Dict[str, Any]] = None,
    ):
        """Send status update - matches SocketEmitter interface"""
        if status not in ["confirm", "processing"]:
            raise ValueError("status must be one of: confirm, processing")

        if system_message is None:
            raise ValueError("system_message is required")

        info_object = {
            "status": status,
            "system_message": system_message,
            "metadata": metadata,
        }

        if user_visible_message is not None:
            info_object["user_visible_message"] = user_visible_message

        await self._emit_http("info", info_object)

    async def send_error(
            self,
            error_type: str,
            message: str,
            user_visible_message: Optional[str] = None,
            code: Optional[str] = None,
            details: Optional[Dict[str, Any]] = None,
    ):
        """Send error - matches SocketEmitter interface"""
        if user_visible_message is None:
            user_visible_message = "Sorry. An error occurred. Please try again."

        error_object = {
            "message": message,
            "type": error_type,
            "user_visible_message": user_visible_message,
        }

        if code:
            error_object["code"] = code
        if details:
            error_object["details"] = self._serialize(details)

        await self._emit_http("error", error_object)

    async def fatal_error(
            self,
            error_type: str,
            message: str,
            user_visible_message: Optional[str] = None,
            code: Optional[str] = None,
            details: Optional[Dict[str, Any]] = None,
    ):
        """Send fatal error and end - matches SocketEmitter interface"""
        await self.send_error(error_type, message, user_visible_message, code, details)
        await self.send_end()

    async def send_end(self):
        """End the stream - matches SocketEmitter interface"""
        if not self._ended:
            await self._emit_http("end")
            self._ended = True
            await self._stream_queue.put(None)  # End signal

    async def send_broker(self, broker: BrokerResponse):
        """Send broker object - matches SocketEmitter interface"""
        if not isinstance(broker, BrokerResponse):
            raise TypeError(f"Expected BrokerResponse dataclass, got {type(broker).__name__}")
        await self._emit_http("broker", broker.to_dict())

    async def send_brokers(self, brokers: List[BrokerResponse]):
        """Send multiple brokers - matches SocketEmitter interface"""
        for broker in brokers:
            await self.send_broker(broker)

    async def send_cancelled(self):
        """Send cancellation - matches SocketEmitter interface"""
        await self.fatal_error(
            error_type="task_cancelled",
            message="Task was cancelled due to system constraints",
            user_visible_message="Your request was cancelled. Please try again."
        )

    def print_sid(self, identifier="None Provided"):
        """Compatibility method - does nothing for HTTP"""
        pass

    async def get_stream(self) -> AsyncGenerator[str, None]:
        """Get the HTTP stream for FastAPI StreamingResponse"""
        while True:
            try:
                message = await asyncio.wait_for(self._stream_queue.get(), timeout=30.0)
                if message is None:  # End signal
                    break
                yield message
            except asyncio.TimeoutError:
                # Send keepalive
                keepalive = \
                    {"keepalive": True},
                yield f"data: {json.dumps(keepalive)}\n\n"
            except Exception as e:
                error_event = {"error": {"type": "stream_error", "message": str(e)}},
                yield f"data: {json.dumps(error_event)}\n\n"
                break

    def _serialize(self, data):
        """Serialize data - same logic as SocketResponse"""
        if data is None or isinstance(data, (bool, int, float, str)):
            return data
        elif isinstance(data, datetime):
            return data.isoformat()
        elif isinstance(data, uuid.UUID):
            return str(data)
        elif isinstance(data, enum.Enum):
            return data.name
        elif dataclasses.is_dataclass(data) and not isinstance(data, type):
            return self._serialize(dataclasses.asdict(data))
        elif isinstance(data, (set, tuple)):
            return [self._serialize(item) for item in data]
        elif isinstance(data, dict):
            return {key: self._serialize(value) for key, value in data.items()}
        elif isinstance(data, list):
            return [self._serialize(item) for item in data]
        elif hasattr(data, "__str__"):
            return str(data)
        return data