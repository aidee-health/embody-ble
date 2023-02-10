"""Communicator module to communicate with an EmBody device over BLE (Bluetooth).

Allows for both sending messages synchronously and asynchronously,
receiving response messages and subscribing for incoming messages from the device.
"""
import asyncio
import logging
import threading
from concurrent.futures import ThreadPoolExecutor
from typing import Optional

import serial
import serial.tools.list_ports
from bleak import BleakClient
from bleak import BleakGATTCharacteristic
from bleak import BleakScanner
from embodycodec import attributes
from embodycodec import codec
from embodyserial import embodyserial

from .exceptions import EmbodyBleError
from .listeners import BleMessageListener
from .listeners import MessageListener
from .listeners import ResponseMessageListener


UART_SERVICE_UUID = "6E400001-B5A3-F393-E0A9-E50E24DCCA9E"
UART_RX_CHAR_UUID = "6E400002-B5A3-F393-E0A9-E50E24DCCA9E"
UART_TX_CHAR_UUID = "6E400003-B5A3-F393-E0A9-E50E24DCCA9E"

EMBODY_NAME_PREFIXES = ["G3_", "EMB"]

asyncio_loop = asyncio.get_event_loop()


class EmbodyBle(embodyserial.EmbodySender):
    """Main class for setting up BLE communication with an EmBody device.

    If serial_port is not set, the first port identified with proper manufacturer name is used.

    Handles both custom EmBody messages being sent on NUS_RX_UUID and received on NUS_TX_UUID,
    as well as standard BLE messages sending/receiving. Different callback interfaces
    (listeners) are used to be notified of incoming EmBody messages (MessageListener) and
    incoming BLE messages (BleMessageListener).

    Separate connect method, since it supports reconnecting to a device as well.
    """

    def __init__(
        self,
        msg_listener: Optional[MessageListener] = None,
        ble_msg_listener: Optional[BleMessageListener] = None,
    ) -> None:
        super().__init__()
        self.__client: Optional[BleakClient] = None
        self.__reader: Optional[_MessageReader] = None
        self.__sender: Optional[_MessageSender] = None
        self.__message_listener = msg_listener
        self.__ble_message_listener = ble_msg_listener

    def connect(self, device_name: Optional[str] = None) -> None:
        return asyncio_loop.run_until_complete(self.async_connect(device_name))

    async def async_connect(self, device_name: Optional[str] = None) -> None:
        """Connect to specified device (or use device name from serial port as default)."""
        if self.__connected() and self.__client:
            await self.__client.disconnect()
        if self.__reader:
            self.__reader.stop()
        if not device_name:
            self.__device_name = self.__find_name_from_serial_port()
        logging.info(f"Using EmBody device name: {self.__device_name}")
        device = await BleakScanner.find_device_by_filter(
            lambda d, ad: d.name and d.name.lower() == self.__device_name.lower()
        )
        if not device:
            raise EmbodyBleError(
                f"Could not find device with name {self.__device_name}"
            )
        self.__client = BleakClient(device, self.on_disconnected)
        await self.__client.connect()
        self.__reader = _MessageReader(self.__client)
        if self.__message_listener:
            self.__reader.add_message_listener(self.__message_listener)
        if self.__ble_message_listener:
            self.__reader.add_ble_message_listener(self.__ble_message_listener)
        self.__sender = _MessageSender(self.__client)
        self.__reader.add_response_message_listener(self.__sender)
        await self.__client.start_notify(
            UART_TX_CHAR_UUID, self.__reader.on_uart_tx_data
        )

    def shutdown(self) -> None:
        """Shutdown after use."""
        self.__sender = None
        if self.__reader:
            self.__reader.stop()
            self.__reader = None

    def send(
        self, msg: codec.Message, timeout: Optional[int] = 30
    ) -> Optional[codec.Message]:
        if not self.__sender:
            raise EmbodyBleError("Sender not initialized")
        return asyncio_loop.run_until_complete(
            self.__sender.send_async(msg, True, timeout)
        )

    def __connected(self) -> bool:
        """Check whether BLE is connected (active handle)"""
        return self.__client is not None and self.__client.is_connected

    def on_disconnected(self, client: BleakClient) -> None:
        """Invoked by bleak when disconnected."""
        logging.debug(f"Disconnected: {client}")

    @staticmethod
    def __find_name_from_serial_port() -> str:
        """Request serial no from EmBody device."""
        comm = embodyserial.EmbodySerial()
        response = comm.send(
            msg=codec.GetAttribute(attributes.SerialNoAttribute.attribute_id), timeout=5
        )
        if not response or not isinstance(response, codec.GetAttributeResponse):
            raise EmbodyBleError(
                "Unable to find connected EmBody device on any serial port or no response received"
            )
        device_name = (
            "G3_"
            + response.value.value.to_bytes(8, "big", signed=True).hex()[-4:].upper()
        )
        comm.shutdown()
        return device_name

    def add_message_listener(self, listener: MessageListener) -> None:
        if self.__reader:
            self.__reader.add_message_listener(listener)

    def add_ble_message_listener(self, listener: BleMessageListener) -> None:
        if self.__reader:
            self.__reader.add_ble_message_listener(listener)

    def add_response_message_listener(self, listener: ResponseMessageListener) -> None:
        if self.__reader:
            self.__reader.add_response_message_listener(listener)


class _MessageSender(ResponseMessageListener):
    """All send functionality is handled by this class.

    This includes thread safety, async handling and windowing
    """

    def __init__(self, client: BleakClient) -> None:
        self.__client = client
        self.__send_lock = threading.Lock()
        self.__response_event = threading.Event()
        self.__current_response_message: Optional[codec.Message] = None

    def response_message_received(self, msg: codec.Message) -> None:
        """Invoked when response message is received by Message reader.

        Sets the local response message and notifies the waiting sender thread
        """
        logging.debug(f"Response message received: {msg}")
        self.__current_response_message = msg
        self.__response_event.set()

    async def send_async(
        self,
        msg: codec.Message,
        wait_for_response: bool = True,
        timeout: Optional[int] = 10,
    ) -> Optional[codec.Message]:
        with self.__send_lock:
            logging.debug(f"Sending message: {msg}, encoded: {msg.encode().hex()}")
            try:
                self.__response_event.clear()
                data = msg.encode()
                logging.debug(f"Sending message over BLE: {msg}")
                await self.__client.write_gatt_char(UART_RX_CHAR_UUID, data)
            except serial.SerialException as e:
                logging.warning(f"Error sending message: {str(e)}", exc_info=False)
                return None
            if wait_for_response:
                if self.__response_event.wait(timeout if timeout else 10):
                    return self.__current_response_message
            return None


class _MessageReader:
    """Process and dispatch incoming messages to subscribers/listeners."""

    def __init__(self, client: BleakClient) -> None:
        """Initialize MessageReader."""
        super().__init__()
        self.__client = client
        self.__message_listener_executor = ThreadPoolExecutor(
            max_workers=1, thread_name_prefix="rcv-worker"
        )
        self.__response_message_listener_executor = ThreadPoolExecutor(
            max_workers=1, thread_name_prefix="rsp-worker"
        )
        self.__ble_message_listener_executor = ThreadPoolExecutor(
            max_workers=1, thread_name_prefix="ble-msg-worker"
        )
        self.__message_listeners: list[MessageListener] = []
        self.__ble_message_listeners: list[BleMessageListener] = []
        self.__response_message_listeners: list[ResponseMessageListener] = []

    def stop(self) -> None:
        self.__message_listener_executor.shutdown(wait=False, cancel_futures=False)
        self.__response_message_listener_executor.shutdown(
            wait=False, cancel_futures=False
        )

    def on_uart_tx_data(self, _: BleakGATTCharacteristic, data: bytearray) -> None:
        """Callback invoked by bleak when a new notification is received.

        New messages, both custom codec messages and BLE messages are received here.
        """
        logging.debug(f"New incoming data UART TX data: {bytes(data).hex()}")
        try:
            pos = 0
            while pos < len(data):
                msg = codec.decode(bytes(data[pos:]))
                logging.debug(f"Decoded message: {msg}")
                self.__handle_incoming_message(msg)
                pos += msg.length
        except Exception as e:
            logging.warning(f"Receive error during incoming message: {e}")

    def on_ble_message_received(
        self, uuid: BleakGATTCharacteristic, data: bytes
    ) -> None:
        """Callback invoked when a new BLE message is received.

        This is invoked by the BLE message listener.
        """
        logging.debug(f"Received BLE message for uuid {uuid}: {data.hex()}")
        self.__handle_ble_message(uuid=uuid.handle, data=data)

    def __handle_incoming_message(self, msg: codec.Message) -> None:
        if msg.msg_type < 0x80:
            self.__handle_message(msg)
        else:
            self.__handle_response_message(msg)

    def __handle_message(self, msg: codec.Message) -> None:
        logging.debug(f"Handling new incoming message: {msg}")
        if len(self.__message_listeners) == 0:
            return
        for listener in self.__message_listeners:
            self.__message_listener_executor.submit(
                _MessageReader.__notify_message_listener, listener, msg
            )

    @staticmethod
    def __notify_message_listener(
        listener: MessageListener, msg: codec.Message
    ) -> None:
        try:
            listener.message_received(msg)
        except Exception as e:
            logging.warning(f"Error notifying listener: {str(e)}", exc_info=True)

    def add_message_listener(self, listener: MessageListener) -> None:
        self.__message_listeners.append(listener)

    def get_ble_message_listeners(self) -> list[BleMessageListener]:
        return self.__ble_message_listeners

    def get_message_listeners(self) -> list[MessageListener]:
        return self.__message_listeners

    def __handle_response_message(self, msg: codec.Message) -> None:
        logging.debug(f"Handling new response message: {msg}")
        if len(self.__response_message_listeners) == 0:
            return
        for listener in self.__response_message_listeners:
            self.__response_message_listener_executor.submit(
                _MessageReader.__notify_rsp_message_listener, listener, msg
            )

    @staticmethod
    def __notify_rsp_message_listener(
        listener: ResponseMessageListener, msg: codec.Message
    ) -> None:
        try:
            listener.response_message_received(msg)
        except Exception as e:
            logging.warning(f"Error notifying listener: {str(e)}", exc_info=True)

    def add_response_message_listener(self, listener: ResponseMessageListener) -> None:
        self.__response_message_listeners.append(listener)

    def __handle_ble_message(self, uuid: int, data: bytes) -> None:
        logging.debug(f"Handling new BLE message. UUID: {uuid}, data: {data.hex()}")
        if len(self.__ble_message_listeners) == 0:
            return
        for listener in self.__ble_message_listeners:
            self.__ble_message_listener_executor.submit(
                _MessageReader.__notify_ble_message_listener, listener, uuid, data
            )

    @staticmethod
    def __notify_ble_message_listener(
        listener: BleMessageListener, uuid: int, data: bytes
    ) -> None:
        try:
            listener.ble_message_received(uuid, data)
        except Exception as e:
            logging.warning(f"Error notifying ble listener: {str(e)}", exc_info=True)

    def add_ble_message_listener(self, listener: BleMessageListener) -> None:
        self.__ble_message_listeners.append(listener)
