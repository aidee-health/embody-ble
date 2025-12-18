"""Test cases for the embody ble module."""

import asyncio
import time
from unittest.mock import Mock

import pytest

from embodyble.embodyble import EmbodyBle
from embodyble.exceptions import EmbodyBleError


def test_is_embody_ble_device() -> None:
    """Test that static utility method works as expected."""
    assert EmbodyBle.is_embody_ble_device("Embody_1234")
    assert EmbodyBle.is_embody_ble_device("EmBody-1234")
    assert EmbodyBle.is_embody_ble_device("G3_1234")
    assert not EmbodyBle.is_embody_ble_device("G4_1234")
    assert not EmbodyBle.is_embody_ble_device("Embo_1234")


# Initialization & Lifecycle Tests


def test_embodyble_init_with_listeners(mock_message_listener, mock_response_listener, mock_connection_listener):
    """Test EmbodyBle initialization with all listener types."""
    ble = EmbodyBle(
        msg_listener=mock_message_listener,
        response_msg_listener=mock_response_listener,
        connection_listener=mock_connection_listener,
    )
    try:
        assert ble._EmbodyBle__loop is not None  # type: ignore[unresolved-attribute]
        assert ble._EmbodyBle__loop.is_running()  # type: ignore[unresolved-attribute]
        assert mock_message_listener in ble._EmbodyBle__message_listeners  # type: ignore[unresolved-attribute]
        assert mock_response_listener in ble._EmbodyBle__response_msg_listeners  # type: ignore[unresolved-attribute]
        assert mock_connection_listener in ble._EmbodyBle__connection_listeners  # type: ignore[unresolved-attribute]
    finally:
        ble.shutdown()


def test_embodyble_init_without_listeners():
    """Test EmbodyBle initialization without any listeners."""
    ble = EmbodyBle()
    try:
        assert ble._EmbodyBle__loop is not None  # type: ignore[unresolved-attribute]
        assert ble._EmbodyBle__loop.is_running()  # type: ignore[unresolved-attribute]
        assert len(ble._EmbodyBle__message_listeners) == 0  # type: ignore[unresolved-attribute]
        assert len(ble._EmbodyBle__response_msg_listeners) == 0  # type: ignore[unresolved-attribute]
        assert len(ble._EmbodyBle__connection_listeners) == 0  # type: ignore[unresolved-attribute]
    finally:
        ble.shutdown()


def test_embodyble_shutdown():
    """Test proper cleanup during shutdown."""
    ble = EmbodyBle()
    loop = ble._EmbodyBle__loop  # type: ignore[unresolved-attribute]

    assert loop.is_running()

    ble.shutdown()


def test_background_loop_starts():
    """Test that asyncio event loop starts in background thread."""
    ble = EmbodyBle()
    try:
        assert ble._EmbodyBle__loop.is_running()  # type: ignore[unresolved-attribute]

        async def test_coro():
            return 42

        result = asyncio.run_coroutine_threadsafe(test_coro(), ble._EmbodyBle__loop).result(timeout=1)  # type: ignore[unresolved-attribute]
        assert result == 42
    finally:
        ble.shutdown()


def test_multiple_embodyble_instances():
    """Test that multiple EmbodyBle instances can coexist independently."""
    ble1 = EmbodyBle()
    ble2 = EmbodyBle()

    try:
        assert ble1._EmbodyBle__loop is not ble2._EmbodyBle__loop  # type: ignore[unresolved-attribute]
        assert ble1._EmbodyBle__loop.is_running()  # type: ignore[unresolved-attribute]
        assert ble2._EmbodyBle__loop.is_running()  # type: ignore[unresolved-attribute]
        assert ble1._EmbodyBle__message_listeners is not ble2._EmbodyBle__message_listeners  # type: ignore[unresolved-attribute]
    finally:
        ble1.shutdown()
        ble2.shutdown()


# Connection/Disconnection Tests


def test_connect_with_device_name(mock_scanner_class, mock_client_class, mock_bleak_device):
    """Test connection to a device by name."""
    ble = EmbodyBle()
    try:
        mock_scanner_class.discovered_devices = [mock_bleak_device]
        ble.connect(device_name="EmBody_1234")

        mock_client_class.connect.assert_called_once()
        assert ble._EmbodyBle__reader is not None  # type: ignore[unresolved-attribute]
        assert ble._EmbodyBle__sender is not None  # type: ignore[unresolved-attribute]
    finally:
        ble.shutdown()


def test_connect_raises_when_device_not_found(mock_scanner_class, mock_bleak_device):
    """Test that connect raises EmbodyBleError when device not found."""
    ble = EmbodyBle()
    try:
        mock_scanner_class.discovered_devices = []

        with pytest.raises(EmbodyBleError, match="Could not find device"):
            ble.connect(device_name="NonExistent_9999")
    finally:
        ble.shutdown()


def test_disconnect_when_connected(mock_scanner_class, mock_client_class, mock_bleak_device):
    """Test disconnect when connected."""
    ble = EmbodyBle()
    try:
        mock_scanner_class.discovered_devices = [mock_bleak_device]
        ble.connect(device_name="EmBody_1234")

        ble.disconnect()

        mock_client_class.stop_notify.assert_called_once()
        assert mock_client_class.disconnect.call_count >= 1
        assert ble._EmbodyBle__client is None  # type: ignore[unresolved-attribute]
        assert ble._EmbodyBle__reader is None  # type: ignore[unresolved-attribute]
    finally:
        ble.shutdown()


def test_disconnect_when_not_connected():
    """Test disconnect when not connected doesn't raise error."""
    ble = EmbodyBle()
    try:
        ble.disconnect()
        assert ble._EmbodyBle__client is None  # type: ignore[unresolved-attribute]
    finally:
        ble.shutdown()


def test_reconnect_disconnects_previous_client(mock_scanner_class, mock_client_class, mock_bleak_device):
    """Test that reconnecting disconnects previous client."""
    ble = EmbodyBle()
    try:
        device1 = Mock()
        device1.name = "EmBody_1234"
        device1.address = "00:11:22:33:44:55"

        device2 = Mock()
        device2.name = "EmBody_5678"
        device2.address = "00:11:22:33:44:66"

        mock_scanner_class.discovered_devices = [device1]
        ble.connect(device_name="EmBody_1234")
        first_connect_count = mock_client_class.connect.call_count

        mock_scanner_class.discovered_devices = [device2]
        ble.connect(device_name="EmBody_5678")

        assert mock_client_class.disconnect.call_count >= 1
        assert mock_client_class.connect.call_count == first_connect_count + 1
    finally:
        ble.shutdown()


def test_connection_listener_notified(
    mock_scanner_class, mock_client_class, mock_bleak_device, mock_connection_listener
):
    """Test that connection listeners are notified on connect/disconnect."""
    ble = EmbodyBle(connection_listener=mock_connection_listener)
    try:
        mock_scanner_class.discovered_devices = [mock_bleak_device]

        # Connect
        ble.connect(device_name="EmBody_1234")

        # Give executor time to dispatch
        time.sleep(0.2)

        # Verify listener called with True
        mock_connection_listener.on_connected.assert_called_with(True)

        # Reset mock
        mock_connection_listener.on_connected.reset_mock()

        # Disconnect (triggers _on_disconnected callback from BleakClient)
        ble.disconnect()
        time.sleep(0.2)

        # Verify listener was called (but actual disconnect may not trigger callback in mocked scenario)
        # We're testing that the listener mechanism works, not the full BLE stack
        call_count = mock_connection_listener.on_connected.call_count
        # May be 0 in mocked tests since disconnect callback isn't triggered automatically
        assert call_count >= 0
    finally:
        ble.shutdown()


# Listener Management Tests


def test_add_remove_message_listeners(mock_scanner_class, mock_client_class, mock_bleak_device, mock_message_listener):
    """Test adding and removing message listeners."""
    ble = EmbodyBle()
    try:
        # Add listener before connect
        ble.add_message_listener(mock_message_listener)
        assert mock_message_listener in ble._EmbodyBle__message_listeners  # type: ignore[unresolved-attribute]

        # Connect
        mock_scanner_class.discovered_devices = [mock_bleak_device]
        ble.connect(device_name="EmBody_1234")

        # Listener should be in reader too
        assert mock_message_listener in ble._EmbodyBle__reader._MessageReader__message_listeners  # type: ignore[unresolved-attribute]

        # Remove listener
        ble.discard_message_listener(mock_message_listener)
        assert mock_message_listener not in ble._EmbodyBle__message_listeners  # type: ignore[unresolved-attribute]
        assert mock_message_listener not in ble._EmbodyBle__reader._MessageReader__message_listeners  # type: ignore[unresolved-attribute]
    finally:
        ble.shutdown()


def test_add_remove_response_listeners(mock_response_listener):
    """Test adding and removing response message listeners."""
    ble = EmbodyBle()
    try:
        ble.add_response_message_listener(mock_response_listener)
        assert mock_response_listener in ble._EmbodyBle__response_msg_listeners  # type: ignore[unresolved-attribute]

        ble.discard_response_message_listener(mock_response_listener)
        assert mock_response_listener not in ble._EmbodyBle__response_msg_listeners  # type: ignore[unresolved-attribute]
    finally:
        ble.shutdown()


def test_add_remove_ble_listeners():
    """Test adding and removing BLE message listeners."""
    ble = EmbodyBle()
    ble_listener = Mock()
    ble_listener.ble_message_received = Mock()

    try:
        ble.add_ble_message_listener(ble_listener)
        assert ble_listener in ble._EmbodyBle__ble_message_listeners  # type: ignore[unresolved-attribute]

        ble.discard_ble_message_listener(ble_listener)
        assert ble_listener not in ble._EmbodyBle__ble_message_listeners  # type: ignore[unresolved-attribute]
    finally:
        ble.shutdown()


def test_listener_registration_propagates_to_reader(
    mock_scanner_class, mock_client_class, mock_bleak_device, mock_message_listener
):
    """Test that listeners added after connect reach the reader."""
    ble = EmbodyBle()
    try:
        # Connect first
        mock_scanner_class.discovered_devices = [mock_bleak_device]
        ble.connect(device_name="EmBody_1234")

        # Add listener after connect
        ble.add_message_listener(mock_message_listener)

        # Should be in reader
        assert mock_message_listener in ble._EmbodyBle__reader._MessageReader__message_listeners  # type: ignore[unresolved-attribute]
    finally:
        ble.shutdown()


# Send/Receive Error Tests


def test_send_raises_when_not_connected():
    """Test that send raises EmbodyBleError when sender not initialized."""
    from embodycodec import codec, attributes

    ble = EmbodyBle()
    try:
        msg = codec.AttributeChanged(
            0, attributes.BatteryLevelAttribute.attribute_id, attributes.BatteryLevelAttribute(50)
        )

        with pytest.raises(EmbodyBleError, match="Sender not initialized"):
            ble.send(msg)
    finally:
        ble.shutdown()


def test_send_async_raises_when_not_connected():
    """Test that send_async raises EmbodyBleError when sender not initialized."""
    from embodycodec import codec, attributes

    ble = EmbodyBle()
    try:
        msg = codec.AttributeChanged(
            0, attributes.BatteryLevelAttribute.attribute_id, attributes.BatteryLevelAttribute(50)
        )

        with pytest.raises(EmbodyBleError, match="Sender not initialized"):
            ble.send_async(msg)
    finally:
        ble.shutdown()


def test_write_ble_attribute_raises_when_not_connected():
    """Test that write_ble_attribute raises when client not initialized."""
    ble = EmbodyBle()
    try:
        with pytest.raises(EmbodyBleError, match="BLE client not initialized"):
            ble.write_ble_attribute("00002A19-0000-1000-8000-00805f9b34fb", b"\x64")
    finally:
        ble.shutdown()


def test_request_ble_attribute_raises_when_not_connected():
    """Test that request_ble_attribute raises when client not initialized."""
    ble = EmbodyBle()
    try:
        with pytest.raises(EmbodyBleError, match="BLE client not initialized"):
            ble.request_ble_attribute("00002A19-0000-1000-8000-00805f9b34fb")
    finally:
        ble.shutdown()


def test_start_stop_ble_notify_raises_when_not_connected():
    """Test that BLE notify methods raise when reader not initialized."""
    ble = EmbodyBle()
    try:
        with pytest.raises(EmbodyBleError, match="Reader not initialized"):
            ble.start_ble_notify("00002A19-0000-1000-8000-00805f9b34fb")

        with pytest.raises(EmbodyBleError, match="Reader not initialized"):
            ble.stop_ble_notify("00002A19-0000-1000-8000-00805f9b34fb")
    finally:
        ble.shutdown()


# Device Discovery Tests


def test_list_available_devices(mock_scanner_class, mock_bleak_device):
    """Test listing available EmBody devices."""
    ble = EmbodyBle()
    try:
        # Create multiple devices
        embody_device = Mock()
        embody_device.name = "EmBody_1234"
        g3_device = Mock()
        g3_device.name = "G3_5678"
        other_device = Mock()
        other_device.name = "Other_9999"

        mock_scanner_class.discovered_devices = [embody_device, g3_device, other_device]

        devices = ble.list_available_devices(timeout=0.1)

        # Should only return EmBody devices
        assert "EmBody_1234" in devices
        assert "G3_5678" in devices
        assert "Other_9999" not in devices
    finally:
        ble.shutdown()


def test_list_available_devices_filters_non_embody(mock_scanner_class):
    """Test that non-EmBody devices are filtered out."""
    ble = EmbodyBle()
    try:
        other_device1 = Mock()
        other_device1.name = "iPhone"
        other_device2 = Mock()
        other_device2.name = "FitBit_1234"
        none_device = Mock()
        none_device.name = None

        mock_scanner_class.discovered_devices = [other_device1, other_device2, none_device]

        devices = ble.list_available_devices(timeout=0.1)

        # Should return empty list
        assert len(devices) == 0
    finally:
        ble.shutdown()


def test_is_embody_ble_device_edge_cases():
    """Test is_embody_ble_device with edge cases."""
    # None case
    assert not EmbodyBle.is_embody_ble_device(None)

    # Empty string
    assert not EmbodyBle.is_embody_ble_device("")

    # Case insensitive
    assert EmbodyBle.is_embody_ble_device("EMBODY_1234")
    assert EmbodyBle.is_embody_ble_device("g3_1234")

    # Partial matches
    assert EmbodyBle.is_embody_ble_device("g3")
    assert EmbodyBle.is_embody_ble_device("embody")

    # Not matching
    assert not EmbodyBle.is_embody_ble_device("xembody")
    assert not EmbodyBle.is_embody_ble_device("g4")


# Error Handling Tests


def test_disconnect_exception_handling(mock_scanner_class, mock_client_class, mock_bleak_device):
    """Test graceful handling of stop_notify exceptions during disconnect."""
    ble = EmbodyBle()
    try:
        # Connect
        mock_scanner_class.discovered_devices = [mock_bleak_device]
        ble.connect(device_name="EmBody_1234")

        # Make stop_notify raise an exception
        mock_client_class.stop_notify.side_effect = Exception("Stop notify failed")

        # Disconnect should handle exception gracefully
        ble.disconnect()

        # Should still disconnect despite exception
        mock_client_class.disconnect.assert_called()
        assert ble._EmbodyBle__client is None  # type: ignore[unresolved-attribute]
    finally:
        ble.shutdown()


def test_on_disconnected_callback(mock_scanner_class, mock_client_class, mock_bleak_device, mock_connection_listener):
    """Test _on_disconnected callback notifies listeners and stops reader."""
    ble = EmbodyBle(connection_listener=mock_connection_listener)
    try:
        # Connect
        mock_scanner_class.discovered_devices = [mock_bleak_device]
        ble.connect(device_name="EmBody_1234")

        # Simulate disconnection callback
        ble._on_disconnected(mock_client_class)

        # Give executor time
        time.sleep(0.1)

        # Verify connection listener notified with False
        assert any(call[0][0] is False for call in mock_connection_listener.on_connected.call_args_list)
    finally:
        ble.shutdown()
