"""Communicator integration tests that use an actual BLE dongle and expects to find an EmBody device."""

import pytest
from embodycodec import attributes
from embodycodec import codec

from embodyble import communicator as blecomm


if not blecomm.EmbodyBleCommunicator.ble_serial_port_present():
    pytest.skip(
        "skipping tests since no ble serial port is available", allow_module_level=True
    )


def test_send_codec_message_and_wait_for_response() -> None:
    """Connect and do a dummy request/response."""
    communicator = blecomm.EmbodyBleCommunicator(device_name="G3_90F9")
    response = communicator.send_message_and_wait_for_response(
        codec.GetAttribute(attributes.SerialNoAttribute.attribute_id)
    )
    assert response.msg_type == codec.GetAttributeResponse.msg_type
    assert isinstance(response, codec.GetAttributeResponse)
    communicator.shutdown()
