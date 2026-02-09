"""Listener interfaces that can be subscribed to by clients."""

from abc import ABC
from abc import abstractmethod

from embodycodec import codec


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


ERROR_TYPE_CRC_ERROR = "crc_error"
ERROR_TYPE_RESYNC = "resync"
ERROR_TYPE_UNKNOWN_MESSAGE = "unknown_message"
ERROR_TYPE_BUFFER_OVERFLOW = "buffer_overflow"


class ErrorListener(ABC):
    """Listener interface for being notified of BLE communication errors."""

    @abstractmethod
    def on_error(self, error_type: str, message: str) -> None:
        """Called when a communication error is detected.

        Args:
            error_type: Type of error - one of ERROR_TYPE_CRC_ERROR, ERROR_TYPE_RESYNC,
                ERROR_TYPE_UNKNOWN_MESSAGE, ERROR_TYPE_BUFFER_OVERFLOW
            message: Human-readable error description
        """
        pass
