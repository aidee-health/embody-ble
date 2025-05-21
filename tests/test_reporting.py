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
