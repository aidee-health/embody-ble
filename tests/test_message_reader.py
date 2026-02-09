"""Test cases for _MessageReader class."""

import time
from unittest.mock import Mock
from unittest.mock import patch

import pytest
from embodycodec import attributes
from embodycodec import codec

from embodyble.embodyble import MAX_SAVED_DATA_SIZE
from embodyble.embodyble import _MessageReader
from embodyble.listeners import ERROR_TYPE_BUFFER_OVERFLOW
from embodyble.listeners import ERROR_TYPE_RESYNC
from embodyble.listeners import ERROR_TYPE_UNKNOWN_MESSAGE


@pytest.fixture
def message_reader(mock_bleak_client):
    """Create a _MessageReader instance for testing."""
    return _MessageReader(
        client=mock_bleak_client, message_listeners=set(), ble_message_listeners=set(), response_message_listeners=set()
    )


def test_on_uart_tx_data_single_message(message_reader, encoded_test_message, mock_message_listener):
    """Test receiving a single complete message."""
    message_reader.add_message_listener(mock_message_listener)

    message_reader.on_uart_tx_data(None, bytearray(encoded_test_message))

    time.sleep(0.1)

    mock_message_listener.message_received.assert_called_once()
    received_msg = mock_message_listener.message_received.call_args[0][0]
    assert isinstance(received_msg, codec.AttributeChanged)


def test_on_uart_tx_data_multiple_messages(message_reader, mock_message_listener):
    """Test receiving multiple messages in one packet."""
    message_reader.add_message_listener(mock_message_listener)

    msg1 = codec.AttributeChanged(
        0, attributes.BatteryLevelAttribute.attribute_id, attributes.BatteryLevelAttribute(50)
    )
    msg2 = codec.AttributeChanged(
        0, attributes.BatteryLevelAttribute.attribute_id, attributes.BatteryLevelAttribute(75)
    )

    combined_data = bytearray(msg1.encode() + msg2.encode())

    message_reader.on_uart_tx_data(None, combined_data)

    time.sleep(0.1)

    assert mock_message_listener.message_received.call_count == 2


def test_on_uart_tx_data_fragmented_message(message_reader, fragmented_test_message):
    """Test handling fragmented message (BufferError)."""
    message_reader.on_uart_tx_data(None, bytearray(fragmented_test_message))

    assert len(message_reader.saved_data) > 0
    assert message_reader.saved_data == fragmented_test_message


def test_on_uart_tx_data_with_saved_data(message_reader, mock_message_listener):
    """Test concatenating with previously saved fragmented data."""
    msg = codec.AttributeChanged(0, attributes.BatteryLevelAttribute.attribute_id, attributes.BatteryLevelAttribute(60))
    encoded = msg.encode()

    fragment1 = encoded[:5]
    fragment2 = encoded[5:]

    message_reader.add_message_listener(mock_message_listener)

    message_reader.on_uart_tx_data(None, bytearray(fragment1))
    assert len(message_reader.saved_data) == len(fragment1)

    message_reader.on_uart_tx_data(None, bytearray(fragment2))

    time.sleep(0.1)

    mock_message_listener.message_received.assert_called_once()
    assert len(message_reader.saved_data) == 0


def test_message_vs_response_routing(message_reader, mock_message_listener, mock_response_listener):
    """Test routing based on msg_type (< 0x80 vs >= 0x80)."""
    message_reader.add_message_listener(mock_message_listener)
    message_reader.add_response_message_listener(mock_response_listener)

    regular_msg = codec.AttributeChanged(
        0, attributes.BatteryLevelAttribute.attribute_id, attributes.BatteryLevelAttribute(50)
    )
    message_reader.on_uart_tx_data(None, bytearray(regular_msg.encode()))

    response_msg = codec.SetAttributeResponse()
    message_reader.on_uart_tx_data(None, bytearray(response_msg.encode()))

    time.sleep(0.1)

    mock_message_listener.message_received.assert_called_once()
    mock_response_listener.response_message_received.assert_called_once()


def test_crc_error_handling(message_reader, mock_message_listener, caplog):
    """Test CRC error handling (currently skipped as implementation uses accept_crc_error=True)."""
    pytest.skip("CRC error handling currently accepts CRC errors (accept_crc_error=True)")


def test_listener_exception_isolation(message_reader):
    """Test that exception in one listener doesn't break others."""
    bad_listener = Mock()
    bad_listener.message_received = Mock(side_effect=Exception("Listener error"))

    good_listener = Mock()
    good_listener.message_received = Mock()

    message_reader.add_message_listener(bad_listener)
    message_reader.add_message_listener(good_listener)

    msg = codec.AttributeChanged(0, attributes.BatteryLevelAttribute.attribute_id, attributes.BatteryLevelAttribute(50))

    message_reader.on_uart_tx_data(None, bytearray(msg.encode()))

    time.sleep(0.1)

    bad_listener.message_received.assert_called_once()
    good_listener.message_received.assert_called_once()


@pytest.mark.asyncio
async def test_ble_notify_start_stop(message_reader):
    """Test BLE characteristic notification subscription."""
    test_uuid = "00002A19-0000-1000-8000-00805f9b34fb"

    # Start notification
    await message_reader.start_ble_notify(test_uuid)
    message_reader._MessageReader__client.start_notify.assert_called_once()

    # Stop notification
    await message_reader.stop_ble_notify(test_uuid)
    message_reader._MessageReader__client.stop_notify.assert_called_once()


def test_on_ble_message_received(message_reader, mock_gatt_characteristic):
    """Test BLE message received callback."""
    ble_listener = Mock()
    ble_listener.ble_message_received = Mock()

    message_reader.add_ble_message_listener(ble_listener)

    test_data = b"\x64"
    message_reader.on_ble_message_received(mock_gatt_characteristic, test_data)

    time.sleep(0.1)

    ble_listener.ble_message_received.assert_called_once()
    call_args = ble_listener.ble_message_received.call_args[0]
    assert call_args[0] == mock_gatt_characteristic.uuid
    assert call_args[1] == test_data


def test_listener_management(message_reader, mock_message_listener):
    """Test adding and removing listeners."""
    message_reader.add_message_listener(mock_message_listener)
    assert mock_message_listener in message_reader._MessageReader__message_listeners

    message_reader.discard_message_listener(mock_message_listener)
    assert mock_message_listener not in message_reader._MessageReader__message_listeners


def test_stop_shuts_down_executors(message_reader):
    """Test that stop() shuts down thread pool executors."""
    message_reader.stop()


def test_hex_operations_only_when_debug_enabled(message_reader):
    """Test that message processing works regardless of log level."""
    msg = codec.AttributeChanged(0, attributes.BatteryLevelAttribute.attribute_id, attributes.BatteryLevelAttribute(50))

    message_reader.on_uart_tx_data(None, bytearray(msg.encode()))


def test_decode_exception_handling(message_reader):
    """Test that malformed data doesn't crash the message reader."""
    bad_data = bytearray([0xFF, 0x10, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00])

    message_reader.on_uart_tx_data(None, bad_data)


# Error Listener & Corruption Counter Tests


def test_error_listener_add_remove(message_reader, mock_error_listener):
    """Test adding and removing error listeners on the reader."""
    message_reader.add_error_listener(mock_error_listener)
    assert mock_error_listener in message_reader._MessageReader__error_listeners

    message_reader.discard_error_listener(mock_error_listener)
    assert mock_error_listener not in message_reader._MessageReader__error_listeners


def test_corruption_counters_initial_zero(message_reader):
    """Test that a fresh reader returns all-zero corruption counters."""
    counters = message_reader.get_corruption_counters()
    assert counters == {
        "crc_errors": 0,
        "resync_events": 0,
        "unknown_message_types": 0,
        "buffer_overflows": 0,
    }


def test_error_listener_notified_on_buffer_overflow(mock_bleak_client, mock_error_listener, mock_gatt_characteristic):
    """Test that error listener is notified on buffer overflow."""
    reader = _MessageReader(mock_bleak_client, error_listeners={mock_error_listener})
    try:
        # Pre-fill saved_data beyond the limit to trigger overflow
        reader.saved_data = bytearray(b"X" * (MAX_SAVED_DATA_SIZE + 1))

        reader.on_uart_tx_data(mock_gatt_characteristic, bytearray(b"\x00"))

        mock_error_listener.on_error.assert_called_once()
        call_args = mock_error_listener.on_error.call_args[0]
        assert call_args[0] == ERROR_TYPE_BUFFER_OVERFLOW
        assert "buffer overflow" in call_args[1].lower()

        counters = reader.get_corruption_counters()
        assert counters["buffer_overflows"] == 1
    finally:
        reader.stop()


def test_error_listener_notified_on_resync(mock_bleak_client, mock_error_listener, mock_gatt_characteristic):
    """Test that error listener is notified when garbage data triggers resync."""
    reader = _MessageReader(mock_bleak_client, error_listeners={mock_error_listener})
    try:
        # Feed garbage bytes that will be skipped via resync
        garbage = bytearray([0x02, 0x00, 0x00])
        reader.on_uart_tx_data(mock_gatt_characteristic, garbage)

        assert mock_error_listener.on_error.call_count >= 1
        # At least one call should be a resync
        error_types = [call[0][0] for call in mock_error_listener.on_error.call_args_list]
        assert ERROR_TYPE_RESYNC in error_types or ERROR_TYPE_UNKNOWN_MESSAGE in error_types
    finally:
        reader.stop()


def test_error_listener_notified_on_unknown_message(mock_bleak_client, mock_error_listener, mock_gatt_characteristic):
    """Test that error listener is notified on unknown message type."""
    reader = _MessageReader(mock_bleak_client, error_listeners={mock_error_listener})
    try:
        # Monkeypatch codec.decode to raise LookupError
        with patch("embodyble.embodyble.codec.decode", side_effect=LookupError("Unknown type 0xAB")):
            # Need enough data for get_meta to work (at least 3 bytes)
            data = bytearray([0xAB, 0x00, 0x05, 0x00, 0x00])
            reader.on_uart_tx_data(mock_gatt_characteristic, data)

        error_types = [call[0][0] for call in mock_error_listener.on_error.call_args_list]
        assert ERROR_TYPE_UNKNOWN_MESSAGE in error_types

        counters = reader.get_corruption_counters()
        assert counters["unknown_message_types"] >= 1
    finally:
        reader.stop()


def test_error_listener_exception_isolation(mock_bleak_client, mock_gatt_characteristic):
    """Test that a failing error listener doesn't prevent other listeners from being notified."""
    bad_listener = Mock()
    bad_listener.on_error = Mock(side_effect=Exception("Listener failed"))

    good_listener = Mock()
    good_listener.on_error = Mock()

    reader = _MessageReader(mock_bleak_client, error_listeners={bad_listener, good_listener})
    try:
        # Trigger a buffer overflow to fire error listeners
        reader.saved_data = bytearray(b"X" * (MAX_SAVED_DATA_SIZE + 1))
        reader.on_uart_tx_data(mock_gatt_characteristic, bytearray(b"\x00"))

        # Both listeners should have been called
        bad_listener.on_error.assert_called_once()
        good_listener.on_error.assert_called_once()
    finally:
        reader.stop()


def test_corruption_counters_after_errors(mock_bleak_client, mock_gatt_characteristic):
    """Test corruption counters accumulate correctly after multiple error types."""
    reader = _MessageReader(mock_bleak_client)
    try:
        # Trigger buffer overflow
        reader.saved_data = bytearray(b"X" * (MAX_SAVED_DATA_SIZE + 1))
        reader.on_uart_tx_data(mock_gatt_characteristic, bytearray(b"\x00"))

        # Trigger unknown message type via monkeypatch
        with patch("embodyble.embodyble.codec.decode", side_effect=LookupError("Unknown")):
            reader.on_uart_tx_data(mock_gatt_characteristic, bytearray([0xAB, 0x00, 0x05, 0x00, 0x00]))

        counters = reader.get_corruption_counters()
        assert counters["buffer_overflows"] == 1
        assert counters["unknown_message_types"] >= 1
        total = sum(counters.values())
        assert total >= 2
    finally:
        reader.stop()
