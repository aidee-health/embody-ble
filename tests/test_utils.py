"""Test cases for utils module (FileReceiver)."""

import io
import time
from unittest.mock import Mock

import pytest
from embodycodec import codec

from embodyble.utils import FileReceiver


@pytest.fixture
def mock_embody_ble():
    """Create a mock EmbodyBle instance."""
    ble = Mock()
    ble.send = Mock()
    ble.add_response_message_listener = Mock()
    ble.discard_response_message_listener = Mock()
    return ble


@pytest.fixture
def file_receiver(mock_embody_ble):
    """Create FileReceiver instance."""
    return FileReceiver(mock_embody_ble)


def test_file_receiver_init(mock_embody_ble):
    """Test FileReceiver initialization registers with EmbodyBle."""
    receiver = FileReceiver(mock_embody_ble)
    mock_embody_ble.add_response_message_listener.assert_called_once_with(receiver)
    assert receiver.receive is False


def test_get_file_success(file_receiver, mock_embody_ble):
    """Test initiating file download."""
    result = file_receiver.get_file("test.bin", 1024)

    assert result == 0
    assert file_receiver.filename == "test.bin"
    assert file_receiver.file_length == 1024
    assert file_receiver.file_position == 0
    assert file_receiver.receive is True
    mock_embody_ble.send.assert_called_once()


def test_get_file_returns_error_when_already_receiving(file_receiver):
    """Test concurrent download prevention."""
    file_receiver.get_file("test1.bin", 1024)
    result = file_receiver.get_file("test2.bin", 2048)
    assert result == -1


def test_receive_file_chunks_in_order(file_receiver):
    """Test sequential chunks update position correctly."""
    file_receiver.get_file("test.bin", 100)

    # First chunk
    chunk1 = codec.FileDataChunk(fileref=1, offset=0, file_data=b"A" * 50)
    file_receiver.response_message_received(chunk1)
    assert file_receiver.file_position == 50

    # Second chunk
    chunk2 = codec.FileDataChunk(fileref=1, offset=50, file_data=b"B" * 50)
    file_receiver.response_message_received(chunk2)
    assert file_receiver.file_position == 100


def test_receive_file_complete_callback(file_receiver):
    """Test done callback invoked on completion."""
    done_callback = Mock()
    file_receiver.get_file("test.bin", 100, done_callback=done_callback)

    chunk = codec.FileDataChunk(fileref=1, offset=0, file_data=b"X" * 100)
    file_receiver.response_message_received(chunk)

    done_callback.assert_called_once()
    args = done_callback.call_args[0]
    assert args[0] == "test.bin"
    assert args[1] == 100
    assert args[3] is None  # No error
    assert file_receiver.receive is False


def test_receive_out_of_order_chunk_error(file_receiver):
    """Test error callback on wrong offset."""
    done_callback = Mock()
    file_receiver.get_file("test.bin", 100, done_callback=done_callback)

    # Send chunk with wrong offset
    chunk = codec.FileDataChunk(fileref=1, offset=50, file_data=b"X" * 50)
    file_receiver.response_message_received(chunk)

    done_callback.assert_called_once()
    args = done_callback.call_args[0]
    assert isinstance(args[3], Exception)  # Error provided
    assert file_receiver.receive is False


def test_receive_oversized_file_warning(file_receiver):
    """Test behavior when file exceeds expected length."""
    done_callback = Mock()
    file_receiver.get_file("test.bin", 50, done_callback=done_callback)

    # Send more data than expected
    chunk = codec.FileDataChunk(fileref=1, offset=0, file_data=b"X" * 100)
    file_receiver.response_message_received(chunk)

    # File transfer should complete despite oversized data
    done_callback.assert_called_once()
    args = done_callback.call_args[0]
    assert args[1] == 100  # Position reached 100
    assert args[3] is None  # No error (just warning logged)
    assert file_receiver.receive is False


def test_progress_callback_invoked(file_receiver):
    """Test progress updates during transfer."""
    progress_callback = Mock()
    file_receiver.get_file("test.bin", 100, progress_callback=progress_callback)

    chunk = codec.FileDataChunk(fileref=1, offset=0, file_data=b"X" * 50)
    file_receiver.response_message_received(chunk)

    progress_callback.assert_called_with("test.bin", 50.0)


def test_stop_listening(file_receiver, mock_embody_ble):
    """Test cleanup removes listener."""
    file_receiver.stop_listening()
    mock_embody_ble.discard_response_message_listener.assert_called_once_with(file_receiver)


def test_ignore_chunks_after_receive_false(file_receiver):
    """Test chunks ignored when not receiving."""
    # Don't call get_file, so receive is False
    chunk = codec.FileDataChunk(fileref=1, offset=0, file_data=b"X" * 50)
    file_receiver.response_message_received(chunk)

    # Position should not change
    assert file_receiver.file_position == 0


def test_datastream_write(file_receiver):
    """Test data written to stream if provided."""
    stream = io.BytesIO()
    file_receiver.get_file("test.bin", 100, datastream=stream)

    chunk = codec.FileDataChunk(fileref=1, offset=0, file_data=b"TEST")
    file_receiver.response_message_received(chunk)

    assert stream.getvalue() == b"TEST"


# Timeout tests


def test_chunk_timeout_triggers_error_callback(file_receiver):
    """Test that inter-chunk timeout calls done_callback with TimeoutError."""
    done_callback = Mock()
    file_receiver.get_file("test.bin", 1000, done_callback=done_callback, chunk_timeout=0.1)

    # Wait for timeout
    time.sleep(0.2)

    done_callback.assert_called_once()
    args = done_callback.call_args[0]
    assert args[0] == "test.bin"
    assert isinstance(args[3], TimeoutError)
    assert file_receiver.receive is False


def test_chunk_timeout_reset_on_chunk_received(file_receiver):
    """Test that receiving a chunk resets the timeout timer."""
    done_callback = Mock()
    file_receiver.get_file("test.bin", 200, done_callback=done_callback, chunk_timeout=0.2)

    # Send first chunk before timeout
    time.sleep(0.1)
    chunk1 = codec.FileDataChunk(fileref=1, offset=0, file_data=b"A" * 100)
    file_receiver.response_message_received(chunk1)

    # Wait again but less than new timeout
    time.sleep(0.1)
    chunk2 = codec.FileDataChunk(fileref=1, offset=100, file_data=b"B" * 100)
    file_receiver.response_message_received(chunk2)

    # File should complete successfully
    assert done_callback.call_count == 1
    args = done_callback.call_args[0]
    assert args[3] is None  # No error


def test_overall_timeout_triggers_error_callback(file_receiver):
    """Test that overall timeout calls done_callback with TimeoutError."""
    done_callback = Mock()
    file_receiver.get_file(
        "test.bin",
        1000,
        done_callback=done_callback,
        chunk_timeout=0.5,  # Long chunk timeout
        overall_timeout=0.1,  # Short overall timeout
    )

    time.sleep(0.2)

    done_callback.assert_called_once()
    args = done_callback.call_args[0]
    assert isinstance(args[3], TimeoutError)
    assert "maximum time" in str(args[3])


def test_timers_cancelled_on_successful_completion(file_receiver):
    """Test that timers are properly cancelled when transfer completes."""
    done_callback = Mock()
    file_receiver.get_file("test.bin", 100, done_callback=done_callback, chunk_timeout=1.0)

    # Complete the transfer
    chunk = codec.FileDataChunk(fileref=1, offset=0, file_data=b"X" * 100)
    file_receiver.response_message_received(chunk)

    # Timers should be cancelled
    assert file_receiver._chunk_timer is None
    assert file_receiver._overall_timer is None


def test_timers_cancelled_on_error(file_receiver):
    """Test that timers are cancelled on out-of-order chunk error."""
    done_callback = Mock()
    file_receiver.get_file("test.bin", 100, done_callback=done_callback, chunk_timeout=1.0)

    # Send out-of-order chunk
    chunk = codec.FileDataChunk(fileref=1, offset=50, file_data=b"X" * 50)
    file_receiver.response_message_received(chunk)

    assert file_receiver._chunk_timer is None


def test_stop_listening_cancels_timers(file_receiver):
    """Test that stop_listening cancels active timers."""
    file_receiver.get_file("test.bin", 1000, chunk_timeout=10.0)

    assert file_receiver._chunk_timer is not None

    file_receiver.stop_listening()

    assert file_receiver._chunk_timer is None
    assert file_receiver.receive is False


def test_no_double_callback_on_race_condition(file_receiver):
    """Test that callback is only called once even with race conditions."""
    done_callback = Mock()
    file_receiver.get_file("test.bin", 100, done_callback=done_callback, chunk_timeout=0.05)

    # Simulate race: chunk arrives just as timeout fires
    time.sleep(0.04)
    chunk = codec.FileDataChunk(fileref=1, offset=0, file_data=b"X" * 100)
    file_receiver.response_message_received(chunk)

    time.sleep(0.1)  # Wait for any pending timeout

    # Should only be called once
    assert done_callback.call_count == 1


def test_default_chunk_timeout_value(file_receiver):
    """Test default chunk timeout is applied."""
    file_receiver.get_file("test.bin", 1000)
    assert file_receiver._chunk_timeout == 10.0  # Default value
    file_receiver.stop_listening()  # Clean up timer


def test_custom_timeout_values(file_receiver):
    """Test custom timeout values are stored."""
    file_receiver.get_file("test.bin", 1000, chunk_timeout=5.0, overall_timeout=60.0)
    assert file_receiver._chunk_timeout == 5.0
    assert file_receiver._overall_timeout == 60.0
    file_receiver.stop_listening()  # Clean up timers
