"""Communicator module to communicate with an EmBody device over BLE (Bluetooth).

Allows for both sending messages synchronously and asynchronously,
receiving response messages and subscribing for incoming messages from the device.
"""
import concurrent.futures
import logging
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from queue import Empty
from queue import Queue
from typing import Optional

import serial
import serial.tools.list_ports
from embodycodec import attributes
from embodycodec import codec
from embodyserial import embodyserial
from pc_ble_driver_py.ble_adapter import BLEAdapter
from pc_ble_driver_py.ble_driver import BLEUUID
from pc_ble_driver_py.ble_driver import BLEAdvData
from pc_ble_driver_py.ble_driver import BLEConfig
from pc_ble_driver_py.ble_driver import BLEConfigConnGap
from pc_ble_driver_py.ble_driver import BLEConfigConnGatt
from pc_ble_driver_py.ble_driver import BLEDriver
from pc_ble_driver_py.ble_driver import BLEGapAddr
from pc_ble_driver_py.ble_driver import BLEGapAdvType
from pc_ble_driver_py.ble_driver import BLEGapConnParams
from pc_ble_driver_py.ble_driver import BLEGapRoles
from pc_ble_driver_py.ble_driver import BLEGapScanParams
from pc_ble_driver_py.ble_driver import BLEHci
from pc_ble_driver_py.ble_driver import BLEUUIDBase
from pc_ble_driver_py.observers import BLEAdapterObserver
from pc_ble_driver_py.observers import BLEDriverObserver
from serial.serialutil import SerialException

from .exceptions import EmbodyBleError
from .listeners import BleMessageListener
from .listeners import MessageListener
from .listeners import ResponseMessageListener


NUS_BASE_UUID = BLEUUIDBase(
    [
        0x6E,
        0x40,
        0x00,
        0x00,
        0xB5,
        0xA3,
        0xF3,
        0x93,
        0xE0,
        0xA9,
        0xE5,
        0x0E,
        0x24,
        0xDC,
        0xCA,
        0x9E,
    ],
    0x02,
)
NUS_RX_UUID = BLEUUID(0x0002, NUS_BASE_UUID)
NUS_TX_UUID = BLEUUID(0x0003, NUS_BASE_UUID)

CFG_TAG = 1
EMBODY_NAME_PREFIXES = ["G3_", "EMB"]


class EmbodyBle(BLEDriverObserver, embodyserial.EmbodySender):
    """Main class for setting up BLE communication with an EmBody device.

    If serial_port is not set, the first port identified with proper manufacturer name is used.

    Handles both custom EmBody messages being sent on NUS_RX_UUID and received on NUS_TX_UUID,
    as well as standard BLE messages sending/receiving. Different callback interfaces
    (listeners) are used to be notified of incoming EmBody messages (MessageListener) and
    incoming BLE messages (BleMessageListener).
    """

    def __init__(
        self,
        msg_listener: Optional[MessageListener] = None,
        ble_msg_listener: Optional[BleMessageListener] = None,
    ) -> None:
        super().__init__()
        self.__ble_serial_port = self.__find_ble_serial_port()
        logging.info(f"Using BLE serial port {self.__ble_serial_port}")
        ble_driver = BLEDriver(
            serial_port=self.__ble_serial_port,
            auto_flash=False,
            baud_rate=1000000,
            log_severity_level="debug",
        )
        self.__conn_q: Queue[int] = Queue()
        self.__ble_conn_handle = -1
        self.__device_name: Optional[str] = None
        self.__candidate_client_list: set[str] = set()
        self.__ble_adapter = self.__setup_ble_adapter(ble_driver)
        self.__reader = _MessageReader()
        self.__ble_adapter.observer_register(self.__reader)
        self.__open_ble_driver()
        if msg_listener:
            self.__reader.add_message_listener(msg_listener)
        if ble_msg_listener:
            self.__reader.add_ble_message_listener(ble_msg_listener)

    def connect(self, device_name: Optional[str] = None) -> None:
        """Connect to specified device (or use device name from serial port as default)."""
        if device_name:
            self.__device_name = device_name
        else:
            self.__device_name = self.__find_name_from_serial_port()
        logging.info(f"Using EmBody device name: {self.__device_name}")
        self.__connect_and_discover()
        self.__sender = _MessageSender(
            ble_adapter=self.__ble_adapter, ble_conn_handle=self.__ble_conn_handle
        )
        self.__reader.add_response_message_listener(self.__sender)

    def discover_candidates(self, timeout: int = 5) -> set[str]:
        """Discover available EmBody devices."""
        self.__candidate_client_list = set()
        orig_name = self.__device_name
        try:
            self.__ble_adapter.driver.ble_gap_scan_start(
                scan_params=BLEGapScanParams(
                    interval_ms=200, window_ms=150, timeout_s=timeout
                )
            )
            time.sleep(timeout)
            return self.__candidate_client_list
        finally:
            self.__device_name = orig_name
            self.__candidate_client_list = set()

    def get_ble_adapter(self) -> BLEAdapter:
        """Get BLE adapter."""
        return self.__ble_adapter

    def get_ble_driver(self) -> BLEDriver:
        """Get BLE driver."""
        return self.__ble_adapter.driver

    def __setup_ble_adapter(self, ble_driver: BLEDriver) -> BLEAdapter:
        """Configure BLE Adapter."""
        adapter = BLEAdapter(ble_driver)
        adapter.driver.observer_register(self)
        adapter.default_mtu = 1500
        adapter.interval = 7.5
        return adapter

    def __open_ble_driver(self) -> None:
        """Open and configure BLE Driver"""
        self.__ble_adapter.driver.open()
        gap_cfg = BLEConfigConnGap()
        gap_cfg.conn_count = 3
        gap_cfg.event_length = int(self.__ble_adapter.interval / 1.25)
        self.__ble_adapter.driver.ble_cfg_set(BLEConfig.conn_gap, gap_cfg)
        gatt_cfg = BLEConfigConnGatt(att_mtu=self.__ble_adapter.default_mtu)
        gatt_cfg.tag = CFG_TAG
        self.__ble_adapter.driver.ble_cfg_set(BLEConfig.conn_gatt, gatt_cfg)
        self.__ble_adapter.driver.ble_enable()
        self.__ble_adapter.driver.ble_vs_uuid_add(NUS_BASE_UUID)

    def __connect_and_discover(self) -> None:
        logging.debug("Discover and connect device")
        scan_duration = 10
        self.__ble_adapter.driver.ble_gap_scan_start(
            scan_params=BLEGapScanParams(
                interval_ms=200, window_ms=150, timeout_s=scan_duration
            )
        )
        try:
            logging.debug(
                "Waiting for connection through driver on_gap_evt_connected callback"
            )
            self.__ble_conn_handle = self.__conn_q.get(timeout=scan_duration)
        except Empty as e:
            raise EmbodyBleError(
                f"Unable to connect to {self.__device_name} within timeout ({scan_duration})"
            ) from e
        self.__ble_adapter.service_discovery(self.__ble_conn_handle)
        # Configure parameters for optimized transfer rate
        self.__ble_adapter.data_length_update(self.__ble_conn_handle, 251)
        att_mtu = self.__ble_adapter.att_mtu_exchange(
            self.__ble_conn_handle, self.__ble_adapter.default_mtu
        )
        logging.debug(
            f"Enabling longer Data Length {self.__ble_adapter.default_mtu} -> {att_mtu}"
        )
        logging.debug("Enabling 2M PHYs")
        req_phys = [0x02, 0x02]
        self.__ble_adapter.phy_update(self.__ble_conn_handle, req_phys)
        logging.debug("Updating connection parameters")
        conn_params = BLEGapConnParams(
            self.__ble_adapter.interval, self.__ble_adapter.interval, 4000, 0
        )
        self.__ble_adapter.conn_param_update(self.__ble_conn_handle, conn_params)

        self.__ble_adapter.enable_notification(self.__ble_conn_handle, NUS_TX_UUID)

    def shutdown(self) -> None:
        """Shutdown after use."""
        self.__ble_adapter.driver.close()
        self.__reader.stop()

    def send_async(self, msg: codec.Message) -> None:
        self.__sender.send_message(msg)

    def send(
        self, msg: codec.Message, timeout: Optional[int] = 30
    ) -> Optional[codec.Message]:
        return self.__sender.send_message_and_wait_for_response(msg, timeout)

    def __connected(self) -> bool:
        """Check whether BLE is connected (active handle)"""
        return self.__ble_conn_handle >= 0

    def on_gap_evt_connected(
        self,
        ble_driver: BLEDriver,
        conn_handle: int,
        peer_addr: BLEGapAddr,
        role: BLEGapRoles,
        conn_params: BLEGapConnParams,
    ) -> None:
        """Implements BLEDriverObserver method"""
        logging.debug(f"Connected: handle #: {conn_handle}.")
        self.__conn_q.put(conn_handle)

    def on_gap_evt_disconnected(
        self, ble_driver: BLEDriver, conn_handle: int, reason: BLEHci
    ) -> None:
        """Implements BLEDriverObserver method"""
        logging.debug(f"Disconnected: {conn_handle} {reason}")
        self.__ble_conn_handle = -1

    def on_gap_evt_adv_report(
        self,
        ble_driver: BLEDriver,
        conn_handle: int,
        peer_addr: BLEGapAddr,
        rssi: int,
        adv_type: BLEGapAdvType,
        adv_data: BLEAdvData,
    ) -> None:
        """Implements BLEDriverObserver method. Used to find address for device name."""
        if self.__connected():
            return
        if BLEAdvData.Types.complete_local_name in adv_data.records:
            dev_name_list = adv_data.records[BLEAdvData.Types.complete_local_name]
        elif BLEAdvData.Types.short_local_name in adv_data.records:
            dev_name_list = adv_data.records[BLEAdvData.Types.short_local_name]
        else:
            return
        dev_name = "".join(chr(e) for e in dev_name_list)
        address_string = "".join(f"{b:02X}" for b in peer_addr.addr)
        logging.debug(
            f"Received advertisement report, address: 0x{address_string}, device_name: {dev_name}"
        )
        if not self.__device_name and any(
            dev_name.startswith(candidate_prefix)
            for candidate_prefix in EMBODY_NAME_PREFIXES
        ):
            self.__candidate_client_list.add(dev_name)
        elif dev_name == self.__device_name:
            logging.debug(
                f"Received advertisement report from our device ({dev_name}). Connecting..."
            )
            self.__ble_adapter.connect(peer_addr, tag=CFG_TAG)

    @staticmethod
    def __find_ble_serial_port() -> str:
        """Find first matching BLE serial port name with NRF dongle attached."""
        ports = serial.tools.list_ports.comports()
        if len(ports) <= 0:
            raise SerialException("No available serial ports")
        else:
            descriptions = ["nRF Connect USB CDC", "nRF52 Connectivity"]
            for port in ports:
                for description in descriptions:
                    if description in port.description:
                        return port.device
        raise EmbodyBleError("No matching serial ports found")

    @staticmethod
    def ble_serial_port_present() -> bool:
        """Helper method to check if an nRF dongle is present."""
        try:
            port = EmbodyBle.__find_ble_serial_port()
            return port is not Empty
        except Exception:
            return False

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
        return device_name


class _MessageSender(ResponseMessageListener):
    """All send functionality is handled by this class.

    This includes thread safety, async handling and windowing
    """

    def __init__(self, ble_adapter: BLEAdapter, ble_conn_handle: int) -> None:
        self.__ble_adapter = ble_adapter
        self.__ble_conn_handle = ble_conn_handle
        self.__send_lock = threading.Lock()
        self.__response_event = threading.Event()
        self.__current_response_message: Optional[codec.Message] = None
        self.__send_executor = ThreadPoolExecutor(
            max_workers=1, thread_name_prefix="send-worker"
        )

    def shutdown(self) -> None:
        self.__send_executor.shutdown(wait=False, cancel_futures=False)

    def response_message_received(self, msg: codec.Message) -> None:
        """Invoked when response message is received by Message reader.

        Sets the local response message and notifies the waiting sender thread
        """
        logging.debug(f"Response message received: {msg}")
        self.__current_response_message = msg
        self.__response_event.set()

    def send_message(self, msg: codec.Message) -> None:
        self.__send_async(msg, False)

    def send_message_and_wait_for_response(
        self, msg: codec.Message, timeout: Optional[int] = 10
    ) -> Optional[codec.Message]:
        future = self.__send_async(msg, True)
        try:
            return future.result(timeout)
        except TimeoutError:
            logging.warning(
                f"No response received for message within timeout: {msg}",
                exc_info=False,
            )
            return None

    def __send_async(
        self, msg: codec.Message, wait_for_response: bool = True
    ) -> concurrent.futures.Future[Optional[codec.Message]]:
        return self.__send_executor.submit(self.__do_send, msg, wait_for_response)

    def __do_send(
        self, msg: codec.Message, wait_for_response: bool = True
    ) -> Optional[codec.Message]:
        with self.__send_lock:
            logging.debug(f"Sending message: {msg}, encoded: {msg.encode().hex()}")
            try:
                self.__response_event.clear()
                data = msg.encode()
                logging.debug(f"Sending message over BLE: {msg}")
                self.__ble_adapter.write_req(self.__ble_conn_handle, NUS_RX_UUID, data)
            except serial.SerialException as e:
                logging.warning(f"Error sending message: {str(e)}", exc_info=False)
                return None
            if wait_for_response:
                if self.__response_event.wait(30):
                    return self.__current_response_message
            return None


class _MessageReader(BLEAdapterObserver):
    """Process and dispatch incoming messages to subscribers/listeners."""

    def __init__(self) -> None:
        """Initialize MessageReader."""
        super().__init__()
        self.__message_listener_executor = ThreadPoolExecutor(
            max_workers=1, thread_name_prefix="rcv-worker"
        )
        self.__response_message_listener_executor = ThreadPoolExecutor(
            max_workers=1, thread_name_prefix="rsp-worker"
        )
        self.__message_listeners: list[MessageListener] = []
        self.__ble_message_listeners: list[BleMessageListener] = []
        self.__response_message_listeners: list[ResponseMessageListener] = []

    def stop(self) -> None:
        self.__message_listener_executor.shutdown(wait=False, cancel_futures=False)
        self.__response_message_listener_executor.shutdown(
            wait=False, cancel_futures=False
        )

    def on_notification(
        self, ble_adapter: BLEAdapter, conn_handle: int, uuid: BLEUUID, data: list[int]
    ) -> None:
        """Implements BLEAdapterObserver method.

        New messages, both custom codec messages and BLE messages are received here.
        """
        hex_data = "".join(f"{x:02x}" for x in data)
        logging.debug(f"New incoming data. Uuid (attribute): {uuid}, data: {hex_data}")
        try:
            if uuid == NUS_TX_UUID:
                # Loop through the data and parse the BLE messages
                pos = 0
                while pos < len(data):
                    msg = codec.decode(bytes(data[pos:]))
                    logging.debug(f"Decoded message: {msg}")
                    self.__handle_incoming_message(msg)
                    pos += msg.length
            else:
                logging.debug(f"Received BLE message for uuid {uuid}")
                self.__handle_ble_message(uuid=uuid, data=data)

        except Exception as e:
            logging.warning(f"Receive error during incoming message: {e}")

    def __handle_incoming_message(self, msg: codec.Message) -> None:
        if msg.msg_type < 0x80:
            self.__handle_message(msg)
        else:
            self.__handle_response_message(msg)

    def __handle_message(self, msg: codec.Message) -> None:
        logging.debug(f"Handling new message: {msg}")
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

    def __handle_ble_message(self, uuid: BLEUUID, data: list[int]) -> None:
        logging.debug(f"Handling new BLE message. UUID: {uuid}")
        if len(self.__ble_message_listeners) == 0:
            return
        for listener in self.__ble_message_listeners:
            self.__ble_message_listener_executor.submit(
                _MessageReader.__notify_ble_message_listener, listener, uuid, data
            )

    @staticmethod
    def __notify_ble_message_listener(
        listener: BleMessageListener, uuid: BLEUUID, data: list[int]
    ) -> None:
        try:
            listener.ble_message_received(uuid, data)
        except Exception as e:
            logging.warning(f"Error notifying ble listener: {str(e)}", exc_info=True)

    def add_ble_message_listener(self, listener: BleMessageListener) -> None:
        self.__ble_message_listeners.append(listener)


if __name__ == "__main__":
    """Main method for demo and testing"""

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(thread)d/%(threadName)s] %(message)s",
    )
    logging.info("Setting up BLE communicator")
    communicator = EmbodyBle()
    communicator.connect(device_name="G3_90F9")
    response = communicator.send_message_and_wait_for_response(
        codec.GetAttribute(attributes.AfeSettingsAllAttribute.attribute_id)
    )
    logging.info(f"Received response: {response}")
    communicator.shutdown()
