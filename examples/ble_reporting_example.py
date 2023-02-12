"""This example shows how to use the reporter module to receive attribute changes from device.

To run this example, you need to have a device connected to your computer.
Run the example with `poetry run python examples/ble_reporting_example.py [device_name]`.
"""
import datetime
import logging
import sys
import time

from embodyble.embodyble import EmbodyBle
from embodyble.reporting import AttributeChangedListener
from embodyble.reporting import EmbodyReporter


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s:%(levelname)s:%(message)s"
    )
    logging.info("Starting BLE reporting example")

    class BleBatteryChangeListener(AttributeChangedListener):
        """a very simple class that implements the AttributeChangedListener interface."""

        def on_battery_level_changed(self, battery_level: int) -> None:
            logging.info(f"Battery level changed to: {battery_level}%")

    embody_ble = EmbodyBle()
    embody_ble.connect(sys.argv[1] if len(sys.argv) > 1 else None)
    reporter = EmbodyReporter(embody_ble, BleBatteryChangeListener())
    reporter.start_ble_battery_level_reporting()
    time.sleep(5)
    reporter.stop_ble_battery_level_reporting()

    manufacturer_name = reporter.read_ble_manufacturer_name()
    logging.info(f"Manufacturer Name: {manufacturer_name}")

    current_time = reporter.read_ble_current_time()
    logging.info(f"Current time: {current_time}")

    battery_level = reporter.read_ble_battery_level()
    logging.info(f"Battery level: {battery_level}%")

    software_revision = reporter.read_ble_software_revision()
    logging.info(f"Software revision: {software_revision}")

    reporter.write_ble_current_time(datetime.datetime.now())

    current_time = reporter.read_ble_current_time()
    logging.info(f"Current time: {current_time}")

    logging.info("Done")
