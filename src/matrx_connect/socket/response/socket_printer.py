import datetime
import enum
import json
import os
import uuid
from typing import Any, Dict, List, Optional

from matrx_utils import print_link, vcprint
from matrx_utils.conf import settings
from matrx_connect.socket.response import BrokerResponse

DEFAULT_SAVE_DIR = os.path.join(settings.TEMP_DIR, "socket_responses")


VERBOSE = True
DEFAULT_ACCUMULATE_RESPONSES = True


class SocketPrinter:
    def __init__(
        self,
        event_name: str,
        sid: str = None,
        namespace: str = "/UserSession",
        debug: bool = False,
        accumulate_responses: bool = DEFAULT_ACCUMULATE_RESPONSES,
    ):
        self.event_name = event_name
        self.sid = sid
        self.namespace = namespace
        self.debug = debug
        self.accumulate_responses = accumulate_responses

        # Response accumulation storage
        if self.accumulate_responses:
            self.accumulated_responses = {
                "text": "",
                "data": [],
                "info": [],
                "error": [],
                "broker": [],
            }

    def print_sid(self, identifier="None Provided"):
        vcprint(
            f"\n\nERROR!\n\n [SOCKET PRINTER] Called By: {identifier}\n\nTHIS IS THE SOCKET PRINTER.\n\nERROR ERROR ERROR\n\n",
            color="yellow",
        )

    async def send_chunk(self, chunk: str):
        vcprint(data=chunk, verbose=VERBOSE, color="green", chunks=True)
        if self.accumulate_responses:
            self.accumulated_responses["text"] += chunk

    async def send_chunk_final(self, chunk: str):
        vcprint(data=chunk, verbose=VERBOSE, color="green", chunks=True)
        if self.accumulate_responses:
            self.accumulated_responses["text"] += chunk
        vcprint(data="End of transmission", title="SocketPrinter.send_chunk_final")
        await self.send_end()

    async def send_data(self, data: Any):
        if not isinstance(data, dict):
            vcprint(
                data=data,
                verbose=VERBOSE,
                title="SocketPrinter.send_data",
                color="green",
            )
            if self.accumulate_responses:
                self.accumulated_responses["data"].append(data)
            return

        if "data" in data:
            vcprint(
                "WARNING! Sending 'data' inside of data doesn't make any sense and will cause errors on the frontend. your data object should be a flat structure with the data you want to send.",
                color="red",
            )
            vcprint(
                "Your object is being modified prior to sending so ensure 'data' is never a key inside of the data, as this causes confusion and unecessary nesting which the frontend cannot process. Flatten structures to send what you're trying to send, without the user of additional layers of complexity.",
                color="yellow",
            )
            nested = data.pop("data")
            if isinstance(nested, dict):
                data.update(nested)
            else:
                data = nested

        vcprint(
            data=data, verbose=VERBOSE, title="SocketPrinter.send_data", color="green"
        )
        if self.accumulate_responses:
            self.accumulated_responses["data"].append(self._serialize(data))

    async def send_data_final(self, data: Any):
        await self.send_data(data)
        vcprint(
            data="End of transmission",
            verbose=VERBOSE,
            title="SocketPrinter.send_data_final",
            color="green",
        )
        await self.send_end()

    async def send_status_update(
        self,
        status: str,
        system_message: Optional[str] = None,
        user_visible_message: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        if status not in ["confirm", "processing"]:
            vcprint(
                "status must be one of: confirm, processing | For Errors and Completion, use send_error and send_end",
                title="Error",
                color="red",
            )
            return

        if system_message is None:
            vcprint("system_message is required", title="Error", color="red")
            return

        info_object = {
            "status": status,
            "system_message": system_message,
            "metadata": metadata,
        }

        if user_visible_message is not None:
            info_object["user_visible_message"] = user_visible_message

        vcprint(
            data=info_object,
            verbose=VERBOSE,
            title="SocketPrinter.send_status_update",
            color="green",
        )
        if self.accumulate_responses:
            self.accumulated_responses["info"].append(self._serialize(info_object))

    async def send_error(
        self,
        error_type: str,
        message: str,
        user_visible_message: Optional[str] = None,
        code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
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

        vcprint(
            data=error_object,
            verbose=VERBOSE,
            title="SocketPrinter.send_error",
            color="green",
        )
        if self.accumulate_responses:
            self.accumulated_responses["error"].append(self._serialize(error_object))

    async def send_end(self):
        vcprint(
            data="End of transmission",
            verbose=VERBOSE,
            title="SocketPrinter.send_end",
            color="green",
        )
        if self.accumulate_responses:
            await self._save_accumulated_responses()

    async def fatal_error(
        self,
        error_type: str,
        message: str,
        user_visible_message: Optional[str] = None,
        code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
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

        vcprint(
            data=error_object,
            verbose=VERBOSE,
            title="SocketPrinter.fatal_error",
            color="red",
        )
        if self.accumulate_responses:
            self.accumulated_responses["error"].append(self._serialize(error_object))
        vcprint(data="End of transmission", title="SocketPrinter.fatal_error")
        if self.accumulate_responses:
            await self._save_accumulated_responses()

    async def _save_accumulated_responses(self):
        """Save accumulated responses to a JSON file with timestamp"""
        if not self.accumulate_responses:
            return

        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S_%f")[
            :-3
        ]  # Include milliseconds
        filename = f"{self.event_name}_{timestamp}.json"
        filepath = os.path.join(DEFAULT_SAVE_DIR, filename)

        # Ensure directory exists
        os.makedirs(DEFAULT_SAVE_DIR, exist_ok=True)

        # Add metadata to the saved file
        output_data = {
            "metadata": {
                "event_name": self.event_name,
                "sid": self.sid,
                "namespace": self.namespace,
                "timestamp": datetime.datetime.now().isoformat(),
                "text_length": len(self.accumulated_responses["text"]),
                "total_data_objects": len(self.accumulated_responses["data"]),
                "total_info_objects": len(self.accumulated_responses["info"]),
                "total_error_objects": len(self.accumulated_responses["error"]),
                "total_broker_objects": len(self.accumulated_responses["broker"]),
            },
            "responses": self.accumulated_responses,
        }

        try:
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(output_data, f, indent=2, ensure_ascii=False)

            vcprint("[SOCKET PRINTER] Accumulated responses saved to", color="pink")
            print_link(filepath)
        except Exception as e:
            vcprint(
                f"Failed to save accumulated responses: {str(e)}",
                title="SocketPrinter",
                color="red",
            )

    # THE FOLLOWING ARE LEGACY METHODS WHICH WILL BE REMOVED SOON. Please stop using them asap!
    async def send_text_chunk(self, text: str):
        vcprint(data=text, verbose=VERBOSE, chunks=True, color="green")
        vcprint(
            "Warning! send_text_chunk is depreciated. Use 'send_chunk' instead.",
            color="red",
        )

    async def send_data_chunk(self, data: Any):
        vcprint(
            data=data,
            verbose=VERBOSE,
            title="SocketPrinter.send_data_chunk",
            color="green",
        )
        vcprint(
            "Warning! send_data_chunk is depreciated. Use 'send_data' instead.",
            color="red",
        )

    async def send_info(self, info: Any):
        vcprint(
            data=info, verbose=VERBOSE, title="SocketPrinter.send_info", color="green"
        )
        vcprint(
            "Warning! send_info is depreciated. Use 'send_status_update' instead.",
            color="red",
        )

    async def send_object(self, obj: any):
        await self.send_data(obj)
        vcprint(
            "Warning! send_object is depreciated. Use 'send_data' instead.", color="red"
        )

    async def finalize_event(self, obj: any):
        await self.send_data_final(obj)
        vcprint(
            "Warning! finalize_event is depreciated. Use 'send_data_final' instead.",
            color="red",
        )

    def _serialize(self, data):
        if data is None or isinstance(
            data, (bool, int, float, str)
        ):  # Preserve JSON-serializable types
            return data
        elif isinstance(data, (datetime.datetime, datetime.date)):
            return data.isoformat()
        elif isinstance(data, uuid.UUID):
            return str(data)
        elif isinstance(data, enum.Enum):
            return data.name
        elif isinstance(data, (set, tuple)):
            return [self._serialize(item) for item in data]
        elif isinstance(data, dict):
            return {key: self._serialize(value) for key, value in data.items()}
        elif isinstance(data, list):
            return [self._serialize(item) for item in data]
        elif hasattr(data, "__str__"):
            return str(data)
        return data

    async def send_broker(self, broker: BrokerResponse):
        """Send a single broker object. Expects a BrokerResponse dataclass."""
        if not isinstance(broker, BrokerResponse):
            raise TypeError(
                f"Expected BrokerResponse dataclass, got {type(broker).__name__}"
            )

        broker_dict = broker.to_dict()
        vcprint(
            data=broker_dict,
            verbose=VERBOSE,
            title="SocketPrinter.send_broker",
            color="green",
        )
        if self.accumulate_responses:
            self.accumulated_responses["broker"].append(broker_dict)

    async def send_brokers(self, brokers: List[BrokerResponse]):
        """Send multiple broker objects. Each must be a BrokerResponse dataclass."""
        if not isinstance(brokers, list):
            raise TypeError(
                f"Expected list of BrokerResponse objects, got {type(brokers).__name__}"
            )

        for broker in brokers:
            if not isinstance(broker, BrokerResponse):
                raise TypeError(
                    f"All items must be BrokerResponse dataclass, found {type(broker).__name__}"
                )
            broker_dict = broker.to_dict()
            vcprint(
                data=broker,
                verbose=VERBOSE,
                title="SocketPrinter.send_brokers",
                color="green",
            )
            if self.accumulate_responses:
                self.accumulated_responses["broker"].append(broker_dict)
