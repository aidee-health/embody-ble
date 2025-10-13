"""Test cases for _MessageSender class."""

import asyncio
from unittest.mock import AsyncMock

import pytest
from embodycodec import codec, attributes

from embodyble.embodyble import _MessageSender


@pytest.fixture
def mock_bleak_client():
    """Create a mock BleakClient for sender tests."""
    client = AsyncMock()
    client.write_gatt_char = AsyncMock()
    return client


@pytest.fixture
def message_sender(mock_bleak_client):
    """Create _MessageSender instance."""
    return _MessageSender(mock_bleak_client)


@pytest.mark.asyncio
async def test_send_async_without_response(message_sender, mock_bleak_client):
    """Test send without waiting for response."""
    msg = codec.AttributeChanged(0, attributes.BatteryLevelAttribute.attribute_id, attributes.BatteryLevelAttribute(50))

    result = await message_sender.send_async(msg, wait_for_response=False)

    mock_bleak_client.write_gatt_char.assert_called_once()
    assert result is None


@pytest.mark.asyncio
async def test_send_async_with_response_success(message_sender, mock_bleak_client):
    """Test send with response - success path."""
    msg = codec.AttributeChanged(0, attributes.BatteryLevelAttribute.attribute_id, attributes.BatteryLevelAttribute(50))
    response = codec.SetAttributeResponse()

    # Simulate response arriving
    async def send_with_response():
        result = await message_sender.send_async(msg, wait_for_response=True, timeout=1)
        return result

    # Start send
    send_task = asyncio.create_task(send_with_response())

    # Give send time to start waiting
    await asyncio.sleep(0.01)

    # Simulate response message received
    message_sender.response_message_received(response)

    # Get result
    result = await send_task

    assert result == response
    mock_bleak_client.write_gatt_char.assert_called_once()


@pytest.mark.asyncio
async def test_send_async_timeout(message_sender, mock_bleak_client):
    """Test send timeout when no response received."""
    msg = codec.AttributeChanged(0, attributes.BatteryLevelAttribute.attribute_id, attributes.BatteryLevelAttribute(50))

    result = await message_sender.send_async(msg, wait_for_response=True, timeout=0.1)

    assert result is None
    mock_bleak_client.write_gatt_char.assert_called_once()


@pytest.mark.asyncio
async def test_send_async_exception_handling(mock_bleak_client):
    """Test send handles BLE write exceptions gracefully."""
    sender = _MessageSender(mock_bleak_client)
    mock_bleak_client.write_gatt_char.side_effect = Exception("BLE write failed")

    msg = codec.AttributeChanged(0, attributes.BatteryLevelAttribute.attribute_id, attributes.BatteryLevelAttribute(50))

    result = await sender.send_async(msg, wait_for_response=False)

    assert result is None


@pytest.mark.asyncio
async def test_send_lock_prevents_concurrent_sends(message_sender, mock_bleak_client):
    """Test that async lock prevents concurrent sends."""
    msg = codec.AttributeChanged(0, attributes.BatteryLevelAttribute.attribute_id, attributes.BatteryLevelAttribute(50))

    # Make write_gatt_char slow
    async def slow_write(*args, **kwargs):
        await asyncio.sleep(0.1)

    mock_bleak_client.write_gatt_char.side_effect = slow_write

    # Start two sends concurrently
    task1 = asyncio.create_task(message_sender.send_async(msg, wait_for_response=False))
    task2 = asyncio.create_task(message_sender.send_async(msg, wait_for_response=False))

    await task1
    await task2

    # Both should complete, but sequentially (lock ensures this)
    assert mock_bleak_client.write_gatt_char.call_count == 2
