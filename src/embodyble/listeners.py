"""Listener interfaces that can be subscribed to by clients."""

from abc import ABC

from pc_ble_driver_py import config


config.__conn_ic_id__ = "NRF52"
from embodycodec import codec
from pc_ble_driver_py.ble_driver import BLEUUID


class MessageListener(ABC):
    """Listener interface for being notified of incoming messages."""

    def message_received(self, msg: codec.Message) -> None:
        """Process received message"""
        pass


class BleMessageListener(ABC):
    """Listener interface for being notified of incoming BLE messages."""

    def ble_message_received(self, uuid: BLEUUID, data: list[int]) -> None:
        """Process received message"""
        pass


class ResponseMessageListener(ABC):
    """Listener interface for being notified of incoming response messages."""

    def response_message_received(self, msg: codec.Message) -> None:
        """Process received response message"""
        pass


class ConnectionListener(ABC):
    """Listener interface for being notified of connection changes."""

    def on_connected(self, connected: bool) -> None:
        """Process connection status."""
        pass
