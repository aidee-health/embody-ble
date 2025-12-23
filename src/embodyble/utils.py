"""Utilities for using embody-ble"""

import io
import logging
import threading
import time
from collections.abc import Callable

from embodycodec import codec
from embodycodec import types

from embodyble.embodyble import EmbodyBle
from embodyble.listeners import ResponseMessageListener

logger = logging.getLogger(__name__)


class FileReceiver(ResponseMessageListener):
    """Utility class to handle messages related to file transfer over BLE"""

    def __init__(
        self,
        embody_ble: EmbodyBle,
    ) -> None:
        logger.warning(f"Init FileReceiver {self}")
        self.embody_ble: EmbodyBle = embody_ble
        self.filename: str = ""
        self.file_length: int = 0
        self.datastream: io.BufferedWriter | None = None
        self.done_callback: Callable[[str, int, io.BufferedWriter | None, Exception | None], None] | None = None
        self.progress_callback: Callable[[str, float], None] | None = None
        self.file_position = 0
        self.file_t0: int | float = 0
        self.file_t1: int | float = 0
        self.file_datarate: float = 0.0
        self.receive = False
        # Timeout configuration
        self._chunk_timeout: float = 10.0
        self._overall_timeout: float | None = None
        self._chunk_timer: threading.Timer | None = None
        self._overall_timer: threading.Timer | None = None
        self._timer_lock: threading.Lock = threading.Lock()
        self.embody_ble.add_response_message_listener(self)

    def stop_listening(self):
        """Cleans up tie-in with embody-ble"""
        self._cancel_all_timers()
        self.receive = False
        self.embody_ble.discard_response_message_listener(self)

    def listen(self):
        """Connects in with embody-ble"""
        self.embody_ble.add_response_message_listener(self)

    def _start_chunk_timer(self) -> None:
        """Start or restart the inter-chunk timeout timer."""
        with self._timer_lock:
            if self._chunk_timer is not None:
                self._chunk_timer.cancel()
            self._chunk_timer = threading.Timer(self._chunk_timeout, self._on_chunk_timeout)
            self._chunk_timer.daemon = True
            self._chunk_timer.start()

    def _reset_chunk_timer(self) -> None:
        """Reset the chunk timer (called when a chunk is received)."""
        self._start_chunk_timer()

    def _start_overall_timer(self) -> None:
        """Start the overall transfer timeout timer."""
        with self._timer_lock:
            if self._overall_timeout is not None:
                self._overall_timer = threading.Timer(self._overall_timeout, self._on_overall_timeout)
                self._overall_timer.daemon = True
                self._overall_timer.start()

    def _cancel_all_timers(self) -> None:
        """Cancel all active timers."""
        with self._timer_lock:
            self._cancel_timers_unsafe()

    def _cancel_timers_unsafe(self) -> None:
        """Cancel timers without acquiring lock (caller must hold lock)."""
        if self._chunk_timer is not None:
            self._chunk_timer.cancel()
            self._chunk_timer = None
        if self._overall_timer is not None:
            self._overall_timer.cancel()
            self._overall_timer = None

    def _on_chunk_timeout(self) -> None:
        """Handle inter-chunk timeout - no chunk received within timeout period."""
        with self._timer_lock:
            if not self.receive:
                return  # Transfer already completed or cancelled
            logger.warning(
                f"File transfer timeout: No chunk received for {self._chunk_timeout}s "
                f"(file: {self.filename!r}, position: {self.file_position}/{self.file_length})"
            )
            self.receive = False
            self._cancel_timers_unsafe()

        if self.done_callback is not None:
            self.done_callback(
                self.filename,
                self.file_position,
                self.datastream,
                TimeoutError(
                    f"File transfer stalled: no data received for {self._chunk_timeout} seconds "
                    f"at position {self.file_position} of {self.file_length} bytes"
                ),
            )

    def _on_overall_timeout(self) -> None:
        """Handle overall transfer timeout - total transfer time exceeded."""
        with self._timer_lock:
            if not self.receive:
                return  # Transfer already completed or cancelled
            elapsed = time.perf_counter() - self.file_t0
            logger.warning(
                f"File transfer overall timeout: Transfer exceeded {self._overall_timeout}s "
                f"(file: {self.filename!r}, elapsed: {elapsed:.1f}s, "
                f"position: {self.file_position}/{self.file_length})"
            )
            self.receive = False
            self._cancel_timers_unsafe()

        if self.done_callback is not None:
            self.done_callback(
                self.filename,
                self.file_position,
                self.datastream,
                TimeoutError(
                    f"File transfer exceeded maximum time of {self._overall_timeout} seconds "
                    f"({self.file_position} of {self.file_length} bytes received)"
                ),
            )

    def response_message_received(self, msg: codec.Message) -> None:
        if isinstance(msg, codec.FileDataChunk):
            filechunk: codec.FileDataChunk = msg
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug(f"Received file chunk! offset={filechunk.offset} length={len(filechunk.file_data)}")
            done = False
            if self.receive is False:  # Ignore all messages after we have rejected the transfer
                return
            # Reset chunk timeout on each received chunk
            self._reset_chunk_timer()
            if self.file_position != filechunk.offset:
                logger.error(
                    "Discarding out of order file chunk of "
                    + f"{len(filechunk.file_data)} bytes for offset "
                    + f"{filechunk.offset} when expecting offset {self.file_position}"
                )
                self._cancel_all_timers()
                if self.done_callback is not None:
                    self.done_callback(
                        self.filename,
                        self.file_position,
                        self.datastream,
                        Exception(
                            "Aborted due to out of order file chunk with fileref "
                            + f"{filechunk.fileref} of {len(filechunk.file_data)} bytes for offset "
                            + f"{filechunk.offset} when expecting offset {self.file_position}"
                        ),
                    )
                self.receive = False
                return
            if self.datastream is not None:
                self.datastream.write(filechunk.file_data)
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug(
                    f"Added {len(filechunk.file_data)} bytes at offset {filechunk.offset} to fileref {filechunk.fileref}"
                )
            self.file_position += len(filechunk.file_data)
            if self.file_position >= self.file_length:
                self.file_t1 = time.perf_counter()
                self.file_datarate = self.file_position / (self.file_t1 - self.file_t0)
            if self.file_position > self.file_length:
                logger.warning(
                    f"File {self.filename!r} received is longer than expected! "
                    + f"Received {self.file_position} bytes of expected {self.file_length} "
                    + f"at a rate of {self.file_datarate:.1f} bytes/s!"
                )
                done = True
            if self.file_position == self.file_length:
                logger.info(
                    f"File {self.filename!r} complete at {self.file_position} bytes at a rate of {self.file_datarate:.1f} bytes/s!"
                )
                done = True
            if self.progress_callback is not None:
                if self.file_length > 0:
                    progress = 100.0 * (self.file_position / self.file_length)
                else:
                    progress = 0.0
                self.progress_callback(self.filename, progress)
            if done:  # Report completion and clean up
                self._cancel_all_timers()
                if self.done_callback is not None:
                    self.done_callback(self.filename, self.file_position, self.datastream, None)
                self.receive = False

    def get_file(
        self,
        filename: str,  # Used for callback to report the progress and completion
        file_length: int,  # File length that we trust is correct!
        datastream: io.BufferedWriter | None = None,  # Stream to write data to as it arrives
        done_callback: (
            Callable[[str, int, io.BufferedWriter | None, Exception | None], None] | None
        ) = None,  # Callback to notify of completed download
        progress_callback: (Callable[[str, float], None] | None) = None,  # Callback to notify about progress
        chunk_timeout: float = 10.0,  # Inter-chunk timeout in seconds
        overall_timeout: float | None = None,  # Optional overall transfer timeout in seconds
    ) -> int:
        if self.receive is True:
            return -1
        self.filename = filename
        self.file_length = file_length
        self.file_position = 0
        self.datastream = datastream
        self.done_callback = done_callback
        self.progress_callback = progress_callback
        self._chunk_timeout = chunk_timeout
        self._overall_timeout = overall_timeout
        self.receive = True
        self.file_t0 = time.perf_counter()
        self._start_chunk_timer()
        if overall_timeout is not None:
            self._start_overall_timer()
        self.embody_ble.send(codec.GetFile(types.File(file_name=filename)))
        return 0
