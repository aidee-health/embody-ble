"""Listener interfaces that can be subscribed to by clients."""

from abc import ABC
from abc import abstractmethod

from embodycodec import codec
from pc_ble_driver_py.ble_driver import BLEUUID


class MessageListener(ABC):
    """Listener interface for being notified of incoming messages."""

    @abstractmethod
    def message_received(self, msg: codec.Message) -> None:
        """Process received message"""
        pass


class BleMessageListener(ABC):
    """Listener interface for being notified of incoming BLE messages."""
    def __init__(self, attribute_id: int):
        self.data_list = []
        self.attribute_id = attribute_id
    
    def ble_message_received(self, uuid: BLEUUID, data: list[int]) -> None:
        """Process received message"""
        if uuid.uuid == self.attribute_id:
            self.data_list.append(data)

        print(data)

    def get_data_list(self):
        return self.data_list
        

class ResponseMessageListener(ABC):
    """Listener interface for being notified of incoming response messages."""

    @abstractmethod
    def response_message_received(self, msg: codec.Message) -> None:
        """Process received response message"""
        pass


class ConnectionListener(ABC):
    """Listener interface for being notified of connection changes."""

    @abstractmethod
    def on_connected(self, connected: bool) -> None:
        """Process connection status."""
        pass
