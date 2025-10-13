"""Test cases for the reporting module."""

import queue

import pytest
from embodycodec import attributes
from embodycodec import codec

from embodyble.reporting import AttributeChangedListener
from embodyble.reporting import AttributeChangedMessageListener


class BlockingQueueAttributeChangedListener(AttributeChangedListener):
    """A simple implementation of AttributeChangedListener that uses queues to block until an attribute changes."""

    def __init__(self) -> None:
        self.battery_level_queue: queue.Queue[int] = queue.Queue()

    def on_battery_level_changed(self, battery_level: int) -> None:
        self.battery_level_queue.put(battery_level)


@pytest.fixture
def attribute_changed_listener() -> BlockingQueueAttributeChangedListener:
    """Return an instance of AttributeChangedListener."""
    return BlockingQueueAttributeChangedListener()


@pytest.fixture
def attribute_changed_message_listener(
    attribute_changed_listener: AttributeChangedListener,
) -> AttributeChangedMessageListener:
    """Return an instance of AttributeChangedMessageListener."""
    return AttributeChangedMessageListener(attr_changed_listener=attribute_changed_listener)


def test_attribute_changed_message_for_battery_level(
    attribute_changed_listener: BlockingQueueAttributeChangedListener,
    attribute_changed_message_listener: AttributeChangedMessageListener,
) -> None:
    """Test the attribute changed message for battery level."""
    attribute_changed_message_listener.message_received(
        codec.AttributeChanged(
            0,
            attributes.BatteryLevelAttribute.attribute_id,
            attributes.BatteryLevelAttribute(50),
        )
    )
    level = attribute_changed_listener.battery_level_queue.get(timeout=1)
    assert level == 50


@pytest.mark.parametrize(
    "attribute,callback_name,expected_value",
    [
        (attributes.BatteryLevelAttribute(75), "on_battery_level_changed", 75),
        (attributes.HeartrateAttribute(72), "on_heart_rate_changed", 72),
        (attributes.BreathRateAttribute(15), "on_breathing_rate_changed", 15),
        (attributes.ChargeStateAttribute(True), "on_charge_state_changed", True),
    ],
)
def test_attribute_routing(attribute, callback_name, expected_value):
    """Test that different attributes route to correct callbacks (DRY with parametrize)."""
    from unittest.mock import Mock

    listener = Mock()
    message_listener = AttributeChangedMessageListener(listener)

    message_listener.message_received(codec.AttributeChanged(0, attribute.attribute_id, attribute))

    # Verify correct callback was called with expected value
    getattr(listener, callback_name).assert_called_once_with(expected_value)


def test_embody_reporter_init():
    """Test EmbodyReporter registers listener correctly."""
    from unittest.mock import Mock
    from embodyble.reporting import EmbodyReporter

    mock_ble = Mock()
    EmbodyReporter(mock_ble)

    mock_ble.add_message_listener.assert_called_once()
    mock_ble.add_ble_message_listener.assert_called_once()


@pytest.mark.parametrize(
    "method_name,expected_msg_type,attribute_id",
    [
        ("start_battery_level_reporting", codec.ConfigureReporting, attributes.BatteryLevelAttribute.attribute_id),
        ("stop_battery_level_reporting", codec.ResetReporting, attributes.BatteryLevelAttribute.attribute_id),
        ("start_heart_rate_reporting", codec.ConfigureReporting, attributes.HeartrateAttribute.attribute_id),
    ],
)
def test_start_stop_reporting_sends_messages(method_name, expected_msg_type, attribute_id):
    """Test that start/stop methods send correct messages (DRY with parametrize)."""
    from unittest.mock import Mock
    from embodyble.reporting import EmbodyReporter

    mock_ble = Mock()
    reporter = EmbodyReporter(mock_ble)

    # Call the method
    if "start" in method_name:
        getattr(reporter, method_name)(1000)
    else:
        getattr(reporter, method_name)()

    # Verify send was called with correct message type
    mock_ble.send.assert_called()
    sent_msg = mock_ble.send.call_args[0][0]
    assert isinstance(sent_msg, expected_msg_type)
    assert sent_msg.attribute_id == attribute_id


@pytest.mark.parametrize(
    "method_name,uuid,expected_value",
    [
        ("read_ble_manufacturer_name", "00002A29-0000-1000-8000-00805f9b34fb", "Aidee"),
        ("read_ble_serial_no", "00002A25-0000-1000-8000-00805f9b34fb", "1234"),
        ("read_ble_battery_level", "00002A19-0000-1000-8000-00805f9b34fb", 85),
    ],
)
def test_ble_read_methods(method_name, uuid, expected_value):
    """Test BLE read methods (DRY with parametrize)."""
    from unittest.mock import Mock
    from embodyble.reporting import EmbodyReporter

    mock_ble = Mock()
    # Setup mock return values
    if isinstance(expected_value, str):
        mock_ble.request_ble_attribute.return_value = bytearray(expected_value.encode("ascii"))
    else:
        mock_ble.request_ble_attribute.return_value = bytearray([expected_value])

    reporter = EmbodyReporter(mock_ble)
    result = getattr(reporter, method_name)()

    mock_ble.request_ble_attribute.assert_called_with(uuid)
    assert result == expected_value


def test_gatt_time_conversion_roundtrip():
    """Test GATT time conversion roundtrip."""
    from datetime import datetime, UTC
    from embodyble.reporting import convert_to_gatt_current_time, convert_from_gatt_current_time

    original = datetime(2025, 10, 13, 14, 30, 45, tzinfo=UTC)
    gatt_bytes = convert_to_gatt_current_time(original)
    restored = convert_from_gatt_current_time(gatt_bytes)

    assert restored.year == original.year
    assert restored.month == original.month
    assert restored.day == original.day
    assert restored.hour == original.hour
    assert restored.minute == original.minute
    assert restored.second == original.second
