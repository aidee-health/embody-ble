"""Shared pytest fixtures for embody-ble tests."""

import asyncio
from unittest.mock import AsyncMock
from unittest.mock import Mock

import pytest
from bleak.backends.characteristic import BleakGATTCharacteristic
from embodycodec import attributes
from embodycodec import codec
from embodyserial import embodyserial
from embodyserial.helpers import EmbodySendHelper


@pytest.fixture
def mock_bleak_device():
    """Create a mock BLE device."""
    device = Mock()
    device.name = "EmBody_1234"
    device.address = "00:11:22:33:44:55"
    return device


@pytest.fixture
def mock_bleak_client(mock_bleak_device):
    """Create a mock BleakClient."""
    client = AsyncMock()
    client.address = mock_bleak_device.address
    client.mtu_size = 247
    client.is_connected = True

    # Mock async methods
    client.connect = AsyncMock()
    client.disconnect = AsyncMock()
    client.start_notify = AsyncMock()
    client.stop_notify = AsyncMock()
    client.write_gatt_char = AsyncMock()
    client.read_gatt_char = AsyncMock(return_value=bytearray(b"\x64"))  # Default: 100

    return client


@pytest.fixture
def mock_bleak_scanner(mock_bleak_device):
    """Create a mock BleakScanner."""
    scanner = AsyncMock()
    scanner.discovered_devices = [mock_bleak_device]
    scanner.start = AsyncMock()
    scanner.stop = AsyncMock()

    # Mock find_device_by_filter to return device
    async def mock_find_device(filter_func):
        for device in scanner.discovered_devices:
            ad = Mock()
            ad.local_name = device.name
            if filter_func(device, ad):
                return device
        return None

    scanner.find_device_by_filter = mock_find_device
    return scanner


@pytest.fixture
def mock_gatt_characteristic():
    """Create a mock BleakGATTCharacteristic."""
    char = Mock(spec=BleakGATTCharacteristic)
    char.uuid = "00002A19-0000-1000-8000-00805f9b34fb"  # Battery level UUID
    return char


@pytest.fixture
def test_battery_level_message():
    """Create a test battery level AttributeChanged message."""
    return codec.AttributeChanged(
        0,  # msg_id
        attributes.BatteryLevelAttribute.attribute_id,
        attributes.BatteryLevelAttribute(75),
    )


@pytest.fixture
def test_heart_rate_message():
    """Create a test heart rate AttributeChanged message."""
    return codec.AttributeChanged(0, attributes.HeartrateAttribute.attribute_id, attributes.HeartrateAttribute(72))


@pytest.fixture
def test_response_message():
    """Create a test response message (msg_type >= 0x80)."""
    return codec.SetAttributeResponse()


@pytest.fixture
def encoded_test_message(test_battery_level_message):
    """Return encoded bytes for a test message."""
    return test_battery_level_message.encode()


@pytest.fixture
def fragmented_test_message():
    """Return a fragmented message (first part only)."""
    msg = codec.AttributeChanged(0, attributes.BatteryLevelAttribute.attribute_id, attributes.BatteryLevelAttribute(50))
    encoded = msg.encode()
    # Return only first 5 bytes to simulate fragmentation
    return encoded[:5]


@pytest.fixture
def mock_embody_serial(monkeypatch):
    """Mock embody-serial to avoid hardware dependency."""
    mock_serial = Mock()
    mock_helper = Mock()
    mock_helper.get_serial_no.return_value = "TEST1234"
    mock_helper.get_firmware_version.return_value = "5.5.0"

    # Mock the EmbodySerial and EmbodySendHelper classes
    monkeypatch.setattr(embodyserial, "EmbodySerial", lambda: mock_serial)
    monkeypatch.setattr(EmbodySendHelper, "__init__", lambda self, sender: None)
    monkeypatch.setattr(EmbodySendHelper, "get_serial_no", lambda self: "TEST1234")
    monkeypatch.setattr(EmbodySendHelper, "get_firmware_version", lambda self: "5.5.0")

    mock_serial.shutdown = Mock()
    return mock_serial


@pytest.fixture
def event_loop():
    """Create an event loop for async tests."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def mock_message_listener():
    """Create a mock MessageListener."""
    listener = Mock()
    listener.message_received = Mock()
    return listener


@pytest.fixture
def mock_response_listener():
    """Create a mock ResponseMessageListener."""
    listener = Mock()
    listener.response_message_received = Mock()
    return listener


@pytest.fixture
def mock_connection_listener():
    """Create a mock ConnectionListener."""
    listener = Mock()
    listener.on_connected = Mock()
    return listener


@pytest.fixture
def mock_scanner_class(mock_bleak_scanner, monkeypatch):
    """Patch BleakScanner to return mock scanner."""

    # Create a mock class that returns our mock scanner instance
    def mock_scanner_init(*args, **kwargs):
        return mock_bleak_scanner

    monkeypatch.setattr("embodyble.embodyble.BleakScanner", lambda *args, **kwargs: mock_bleak_scanner)
    return mock_bleak_scanner


@pytest.fixture
def mock_client_class(mock_bleak_client, monkeypatch):
    """Patch BleakClient to return mock client."""

    # Create a mock class that returns our mock client instance
    def mock_client_init(device, disconnected_callback=None, *args, **kwargs):
        # Store the disconnected callback for testing
        mock_bleak_client._disconnected_callback = disconnected_callback
        return mock_bleak_client

    monkeypatch.setattr("embodyble.embodyble.BleakClient", mock_client_init)
    return mock_bleak_client
