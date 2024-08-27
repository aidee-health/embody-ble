"""Utilities for using embody-ble"""

import io
import logging
import time
from typing import Callable
from typing import Optional

from embodycodec import codec
from embodycodec import types

from embodyble.embodyble import EmbodyBle
from embodyble.listeners import ResponseMessageListener


class FileReceiver(ResponseMessageListener):
    """Utility class to handle messages related to file transfer over BLE"""

    def __init__(
        self,
        embody_ble: EmbodyBle,
    ) -> None:
        logging.warning(f"Init FileReceiver {self}")
        self.embody_ble: EmbodyBle = embody_ble
        self.filename: str = ""
        self.file_length: int = 0
        self.datastream: io.BufferedWriter | None = None
        self.done_callback: (
            Callable[[str, int, io.BufferedWriter | None, Exception | None], None]
            | None
        ) = None
        self.progress_callback: Callable[[str, float], None] | None = None
        self.file_position = 0
        self.file_t0: int | float = 0
        self.file_t1: int | float = 0
        self.receive = False
        self.embody_ble.add_response_message_listener(self)

    def stop_listening(self):
        """Cleans up tie-in with embody-ble"""
        self.embody_ble.discard_response_message_listener(self)

    def listen(self):
        """Connects in with embody-ble"""
        self.embody_ble.add_response_message_listener(self)

    def response_message_received(self, msg: codec.Message) -> None:
        if isinstance(msg, codec.FileDataChunk):
            filechunk: codec.FileDataChunk = msg
            logging.debug(
                f"Received file chunk! offset={filechunk.offset} length={len(filechunk.file_data)}"
            )
            done = False
            if (
                self.receive is False
            ):  # Ignore all messages after we have rejected the transfer
                return
            if self.file_position != filechunk.offset:
                logging.error(
                    "Discarding out of order file chunk of "
                    + f"{len(filechunk.file_data)} bytes for offset "
                    + f"{filechunk.offset} when expecting offset {self.file_position}"
                )
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
            logging.debug(
                f"Added {len(filechunk.file_data)} bytes at offset {filechunk.offset} to fileref {filechunk.fileref}"
            )
            self.file_position += len(filechunk.file_data)
            if self.file_position >= self.file_length:
                self.file_t1 = time.perf_counter()
                self.file_datarate = self.file_position / (self.file_t1 - self.file_t0)
            if self.file_position > self.file_length:
                logging.warning(
                    f"File {self.filename!r} received is longer than expected! "
                    + f"Received {self.file_position} bytes of expected {self.file_length} "
                    + f"at a rate of {self.file_datarate:.1f} bytes/s!"
                )
                done = True
            if self.file_position == self.file_length:
                logging.info(
                    f"File {self.filename!r} complete at {self.file_position} bytes at a rate of {self.file_datarate:.1f} bytes/s!"
                )
                done = True
            if self.progress_callback is not None:
                self.progress_callback(
                    self.filename, 100.0 * (self.file_position / self.file_length)
                )
            if done:  # Report completion and clean up
                if self.done_callback is not None:
                    self.done_callback(
                        self.filename, self.file_position, self.datastream, None
                    )
                self.receive = False

    def get_file(
        self,
        filename: str,  # Used for callback to report the progress and completion
        file_length: int,  # File length that we trust is correct!
        datastream: Optional[
            io.BufferedWriter
        ] = None,  # Stream to write data to as it arrives
        done_callback: (
            Callable[[str, int, io.BufferedWriter | None, Exception | None], None]
            | None
        ) = None,  # Callback to notify of completed download
        progress_callback: (
            Optional[Callable[[str, float], None]] | None
        ) = None,  # Callback to notify about progress
    ) -> int:
        if self.receive is True:
            return -1
        self.filename = filename
        self.file_length = file_length
        self.file_position = 0
        self.datastream = datastream
        self.done_callback = done_callback
        self.progress_callback = progress_callback
        self.receive = True
        self.file_t0 = time.perf_counter()
        self.embody_ble.send(codec.GetFile(types.File(file_name=filename)))
        return 0
