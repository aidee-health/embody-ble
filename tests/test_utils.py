"""Test cases for utils module (FileReceiver)."""

import io
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
