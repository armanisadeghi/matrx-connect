import dataclasses
from typing import Any, Optional


@dataclasses.dataclass
class BrokerResponse:
    """Simple dataclass for broker objects sent via socket responses"""

    broker_id: str
    value: Any
    source: Optional[str] = None
    source_id: Optional[str] = None

    def to_dict(self) -> dict:
        """Convert the dataclass to a dictionary for socket.io compatibility"""
        return dataclasses.asdict(self)
