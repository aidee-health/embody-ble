"""Listener interfaces that can be subscribed to by clients."""

from abc import ABC
from abc import abstractmethod
from enum import StrEnum
from typing import NotRequired, TypedDict

from embodycodec import codec


class ConnectionInfo(TypedDict):
    """Connection diagnostic information."""

    connected: bool
    device_name: str | None
    mtu_size: int | None
    device_address: NotRequired[str]


class BleErrorType(StrEnum):
    """Types of BLE communication errors."""

    CRC_ERROR = "crc_error"
    RESYNC = "resync"
    UNKNOWN_MESSAGE = "unknown_message"
    BUFFER_OVERFLOW = "buffer_overflow"


# Backwards-compatible aliases
ERROR_TYPE_CRC_ERROR = BleErrorType.CRC_ERROR
ERROR_TYPE_RESYNC = BleErrorType.RESYNC
ERROR_TYPE_UNKNOWN_MESSAGE = BleErrorType.UNKNOWN_MESSAGE
ERROR_TYPE_BUFFER_OVERFLOW = BleErrorType.BUFFER_OVERFLOW


class MessageListener(ABC):
    """Listener interface for being notified of incoming messages."""

    @abstractmethod
    def message_received(self, msg: codec.Message) -> None:
        """Process received message"""


class BleMessageListener(ABC):
    """Listener interface for being notified of incoming BLE messages."""

    @abstractmethod
    def ble_message_received(self, uuid: str, data: bytes | bytearray) -> None:
        """Process received message"""


class ResponseMessageListener(ABC):
    """Listener interface for being notified of incoming response messages."""

    @abstractmethod
    def response_message_received(self, msg: codec.Message) -> None:
        """Process received response message"""


class ConnectionListener(ABC):
    """Listener interface for being notified of connection changes."""

    @abstractmethod
    def on_connected(self, connected: bool) -> None:
        """Process connection status."""
        pass


class ErrorListener(ABC):
    """Listener interface for being notified of BLE communication errors."""

    @abstractmethod
    def on_error(self, error_type: BleErrorType, message: str) -> None:
        """Called when a communication error is detected.

        Args:
            error_type: Type of error (see BleErrorType enum)
            message: Human-readable error description
        """
        pass
