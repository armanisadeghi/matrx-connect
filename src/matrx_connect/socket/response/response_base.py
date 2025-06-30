import asyncio
import dataclasses
import datetime
import enum
import uuid

from matrx_connect import sio
from matrx_connect.socket.response.response_types import BrokerResponse
from matrx_utils import vcprint

local_debug = False


class SocketResponse:
    def __init__(
        self,
        event_name: str,
        sid: str,
        namespace: str = "/UserSession",
        debug: bool = False,
    ):
        self.event_name = event_name
        self.sid = sid
        self.namespace = namespace
        self._sio = sio
        self.debug = local_debug or debug
        self._initialize()

    def _initialize(self):
        try:
            # Use await instead of asyncio.create_task to ensure initialization completes
            loop = asyncio.get_running_loop()
            future = loop.run_in_executor(
                None,
                lambda: self._sio.emit(
                    "incoming_stream_event",
                    {"event_name": self.event_name},
                    to=self.sid,
                    namespace=self.namespace,
                ),
            )
            asyncio.ensure_future(future)
            vcprint(
                self.event_name,
                title="[SOCKET RESPONSE] INIT With Event Name",
                color="gold",
            )
        except Exception as e:
            vcprint(
                data=e, title="[SOCKET RESPONSE] Initialization Exception", color="red"
            )
            raise RuntimeError(f"Failed to initialize SocketResponse: {str(e)}") from e

    async def _send_chunk(self, chunk):
        try:
            await self._sio.emit(
                self.event_name, chunk, to=self.sid, namespace=self.namespace
            )
        except Exception as e:
            vcprint(data=e, title="[SOCKET RESPONSE] Send Chunk Exception", color="red")
            raise RuntimeError(f"Failed to send chunk: {str(e)}") from e

    async def _send_data(self, data):
        try:
            response = {"data": self._serialize(data)}
            await self._sio.emit(
                self.event_name, response, to=self.sid, namespace=self.namespace
            )
            self._debug_print(response, "_send_data")
        except Exception as e:
            vcprint(data=e, title="[SOCKET RESPONSE] Send Data Exception", color="red")
            raise RuntimeError(f"Failed to send data: {str(e)}") from e

    async def _send_info(self, info_object):
        try:
            response = {"info": info_object}
            await self._sio.emit(
                self.event_name, response, to=self.sid, namespace=self.namespace
            )
            self._debug_print(response, "_send_info")
        except Exception as e:
            vcprint(data=e, title="[SOCKET RESPONSE] Send Info Exception", color="red")
            raise RuntimeError(f"Failed to send info: {str(e)}") from e

    async def _send_broker(self, broker_object: BrokerResponse):
        try:
            response = {"broker": broker_object}
            await self._sio.emit(
                self.event_name, response, to=self.sid, namespace=self.namespace
            )
            self._debug_print(response, "_send_broker")
        except Exception as e:
            vcprint(
                data=e, title="[SOCKET RESPONSE] Send Broker Exception", color="red"
            )
            raise RuntimeError(f"Failed to send broker: {str(e)}") from e

    async def _send_error(self, error_object):
        try:
            response = {"error": error_object}
            await self._sio.emit(
                self.event_name, response, to=self.sid, namespace=self.namespace
            )
            self._debug_print(response, "_send_error")
        except Exception as e:
            vcprint(data=e, title="[SOCKET RESPONSE] Send Error Exception", color="red")
            raise RuntimeError(f"Failed to send error: {str(e)}") from e

    async def _send_end(self):
        try:
            response = {"end": True}
            await self._sio.emit(
                self.event_name, response, to=self.sid, namespace=self.namespace
            )
            self._debug_print(response, "_send_end")
        except Exception as e:
            vcprint(data=e, title="[SOCKET RESPONSE] Send End Exception", color="red")
            raise RuntimeError(f"Failed to send end: {str(e)}") from e

    def _debug_print(self, data, method_name):
        if not self.debug:
            return
        title = f"[SOCKET RESPONSE] {method_name} for event: {self.event_name}"
        vcprint(data=data, title=title, color="blue")

    def _serialize(self, data):
        if data is None or isinstance(data, (bool, int, float, str)):
            return data
        elif isinstance(data, (datetime.datetime, datetime.date)):
            return data.isoformat()
        elif isinstance(data, uuid.UUID):
            return str(data)
        elif isinstance(data, enum.Enum):
            return data.name
        elif dataclasses.is_dataclass(data) and not isinstance(data, type):
            return self._serialize(dataclasses.asdict(data))
        elif hasattr(data, "__dataclass_fields__") and not isinstance(data, type):
            # Fallback for dataclass-like objects that might not be detected by is_dataclass
            try:
                return self._serialize(dataclasses.asdict(data))
            except (TypeError, AttributeError):
                # If asdict fails, fall through to other serialization methods
                pass
        elif isinstance(data, (set, tuple)):
            return [self._serialize(item) for item in data]
        elif isinstance(data, dict):
            return {key: self._serialize(value) for key, value in data.items()}
        elif isinstance(data, list):
            return [self._serialize(item) for item in data]
        elif hasattr(data, "__str__"):
            return str(data)
        return data
