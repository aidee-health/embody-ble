"""Initialize the embodyble package."""

import importlib.metadata as importlib_metadata
import logging

# Configure NullHandler by default to prevent unwanted logging output
_library_logger = logging.getLogger("embodyble")
if not _library_logger.handlers:
    _library_logger.addHandler(logging.NullHandler())


try:
    # This will read version from pyproject.toml
    __version__ = importlib_metadata.version("embody-ble")
except Exception:
    __version__ = "unknown"
