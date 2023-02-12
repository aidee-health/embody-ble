"""Initialize the embodyble package."""
import importlib.metadata as importlib_metadata


try:
    # This will read version from pyproject.toml
    __version__ = importlib_metadata.version("embody-ble")
except Exception:
    __version__ = "unknown"
