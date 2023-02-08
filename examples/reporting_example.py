"""This example shows how to use the reporter module to receive attribute changes from device.

To run this example, you need to have a device connected to your computer.
Run the example with `poetry run python examples/reporting_example.py`.
"""
import logging
import time

from embodyble.attrlistener import AttributeChangedListener
from embodyble.embodyble import EmbodyBle
from embodyble.reporter import EmbodyReporter


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s:%(levelname)s:%(message)s"
    )
    logging.info("Starting reporting example")

    class BatteryChangeListener(AttributeChangedListener):
        """a very simple class that implements the AttributeChangedListener interface."""

        def on_battery_level_changed(self, battery_level: int) -> None:
            logging.info(f"Battery level changed to: {battery_level}%")

    embody_ble = EmbodyBle()
    reporter = EmbodyReporter(embody_ble, BatteryChangeListener())
    embody_ble.connect()
    reporter.start_battery_level_reporting(int_seconds=1)
    time.sleep(30)
    reporter.stop_all_reporting()
