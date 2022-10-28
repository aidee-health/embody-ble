"""Communicator integration tests that use an actual BLE dongle and expects to find an EmBody device."""

from unittest.mock import Mock

from embodycodec import attributes
from embodycodec import codec
from pc_ble_driver_py.ble_adapter import BLEAdapter

from embodyble import embodyble


def test_send_asynch() -> None:
    """Connect and do a dummy request/response."""
    ble_adapter: BLEAdapter = Mock()
    sender = embodyble._MessageSender(ble_adapter=ble_adapter, ble_conn_handle=1)
    sender.send_message(
        msg=codec.GetAttribute(attributes.SerialNoAttribute.attribute_id)
    )
