"""Communicator module to communicate with an EmBody device over BLE (Bluetooth).

Allows for both sending messages synchronously and asynchronously,
receiving response messages and subscribing for incoming messages from the device.
"""
import logging
from queue import Empty
from queue import Queue

import serial
import serial.tools.list_ports
from embodycodec import attributes
from embodycodec import codec
from embodyserial import communicator as serialcomm
from pc_ble_driver_py import config
from pc_ble_driver_py.observers import BLEAdapterObserver
from pc_ble_driver_py.observers import BLEDriverObserver
from serial.serialutil import SerialException

from embodyble.exceptions import EmbodyBleError


config.__conn_ic_id__ = "NRF52"

from pc_ble_driver_py.ble_adapter import BLEAdapter
from pc_ble_driver_py.ble_driver import BLEUUID
from pc_ble_driver_py.ble_driver import BLEAdvData
from pc_ble_driver_py.ble_driver import BLEConfig
from pc_ble_driver_py.ble_driver import BLEConfigConnGap
from pc_ble_driver_py.ble_driver import BLEConfigConnGatt
from pc_ble_driver_py.ble_driver import BLEDriver
from pc_ble_driver_py.ble_driver import BLEGapConnParams
from pc_ble_driver_py.ble_driver import BLEGapScanParams
from pc_ble_driver_py.ble_driver import BLEUUIDBase


global nrf_sd_ble_api_ver
nrf_sd_ble_api_ver = config.sd_api_ver_get()
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


class EmbodyBleCommunicator(BLEDriverObserver, BLEAdapterObserver):
    """Main class for setting up communication with an EmBody device.

    If serial_port is not set, the first port identified with proper manufacturer name is used.
    """

    def __init__(self, ble_serial_port: str = None, device_name: str = None) -> None:
        super().__init__()
        if ble_serial_port:
            self.__ble_serial_port = ble_serial_port
        else:
            self.__ble_serial_port = self.__find_ble_serial_port()
        logging.info(f"Using BLE serial port {self.__ble_serial_port}")
        if device_name:
            self.__device_name = device_name
        else:
            self.__device_name = self.__find_name_from_serial_port()
        logging.info(f"Using EmBody device name: {self.__device_name}")
        ble_driver = BLEDriver(
            serial_port=self.__ble_serial_port,
            auto_flash=False,
            baud_rate=1000000,
            log_severity_level="debug",
        )
        self.__conn_q = Queue()
        self.__ble_conn_handle: int = None
        self.__ble_adapter = self.__setup_ble_adapter(ble_driver)
        self.__open_ble_driver()
        self.__connect_and_discover()

    def __setup_ble_adapter(self, ble_driver: BLEDriver) -> BLEAdapter:
        """Configure BLE Adapter"""
        adapter = BLEAdapter(ble_driver)
        adapter.observer_register(self)
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
        logging.info("Discover and connect device")
        scan_duration = 5
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
        logging.info(
            f"Enabling longer Data Length {self.__ble_adapter.default_mtu} -> {att_mtu}"
        )
        logging.info("Enabling 2M PHYs")
        req_phys = [0x02, 0x02]
        self.__ble_adapter.phy_update(self.__ble_conn_handle, req_phys)
        logging.info("Updating connection parameters")
        conn_params = BLEGapConnParams(
            self.__ble_adapter.interval, self.__ble_adapter.interval, 4000, 0
        )
        self.__ble_adapter.conn_param_update(self.__ble_conn_handle, conn_params)

        self.__ble_adapter.enable_notification(self.__ble_conn_handle, NUS_TX_UUID)

    def shutdown(self):
        """Shutdown after use."""
        self.__ble_adapter.driver.close()

    def send_message(self, msg: codec.Message) -> None:
        data = msg.encode()
        logging.info(f"Sending message over BLE: {msg}")
        self.__ble_adapter.write_req(self.__ble_conn_handle, NUS_RX_UUID, data)

    def on_gap_evt_connected(
        self, ble_driver, conn_handle, peer_addr, role, conn_params
    ):
        """Implements BLEDriverObserver method"""
        logging.info(f"Connected: handle #: {conn_handle}")
        self.__conn_q.put(conn_handle)

    def on_gap_evt_disconnected(self, ble_driver, conn_handle, reason):
        """Implements BLEDriverObserver method"""
        logging.info(f"Disconnected: {conn_handle} {reason}")
        self.__ble_conn_handle = None

    def on_gap_evt_adv_report(
        self, ble_driver, conn_handle, peer_addr, rssi, adv_type, adv_data
    ):
        """Implements BLEDriverObserver method. Used to find address for device name."""
        if self.__ble_conn_handle:
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
        if dev_name == self.__device_name:
            logging.info(
                f"Received advertisement report from our device ({dev_name}). Connecting..."
            )
            self.__ble_adapter.connect(peer_addr, tag=CFG_TAG)

    def on_notification(self, ble_adapter, conn_handle, uuid, data):
        """Implements BLEAdapterObserver method"""
        logging.info(f"New incoming data. Uuid (attribute): {uuid}")
        try:
            if uuid == NUS_TX_UUID:
                # Loop through the data and parse the BLE messages
                pos = 0
                while pos < len(data):
                    msg = codec.decode(bytes(data[pos:]))
                    logging.info(f"Decoded message: {msg}")
                    pos += msg.length
            else:
                logging.info(f"Unsubscribed uuid {uuid} - skipping")
        except Exception as e:
            logging.warning(f"Receive error during incoming message: {e}")

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
    def __find_name_from_serial_port() -> str:
        comm = serialcomm.EmbodySerialCommunicator()
        response = comm.send_message_and_wait_for_response(
            msg=codec.GetAttribute(attributes.SerialNoAttribute.attribute_id), timeout=3
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


if __name__ == "__main__":
    """Main method for demo and testing"""
    import time

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(thread)d/%(threadName)s] %(message)s",
    )
    logging.info("Setting up BLE communicator")
    communicator = EmbodyBleCommunicator(device_name=None)
    communicator.send_message(
        codec.GetAttribute(attributes.SerialNoAttribute.attribute_id)
    )
    time.sleep(5)
    communicator.shutdown()
