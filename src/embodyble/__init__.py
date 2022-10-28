"""Initialize the embodyble package."""
import importlib.metadata as importlib_metadata

from pc_ble_driver_py import config


# Configure nordic pc-ble-driver-py settings
config.__conn_ic_id__ = "NRF52"
nrf_sd_ble_api_ver = config.sd_api_ver_get()

try:
    # This will read version from pyproject.toml
    __version__ = importlib_metadata.version(__name__)
except Exception:
    __version__ = "unknown"
