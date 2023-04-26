"""Test cases for the embody ble module."""

from embodyble.embodyble import EmbodyBle


def test_is_embody_ble_device() -> None:
    """Test that static utility method works as expected."""
    assert EmbodyBle.is_embody_ble_device("Embody_1234")
    assert EmbodyBle.is_embody_ble_device("EmBody-1234")
    assert EmbodyBle.is_embody_ble_device("G3_1234")
    assert not EmbodyBle.is_embody_ble_device("G4_1234")
    assert not EmbodyBle.is_embody_ble_device("Embo_1234")
