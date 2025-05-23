"""This example shows how to use the reporter module to receive attribute changes from device.

To run this example, you need to have a device connected to your computer.
Run the example with `poetry run python examples/reporting_example.py [device_name]`.
"""

import logging
import sys
import time

from embodyble.embodyble import EmbodyBle
from embodyble.reporting import AttributeChangedListener
from embodyble.reporting import EmbodyReporter


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s:%(levelname)s:%(message)s")
    logging.info("Starting reporting example")

    class BatteryChangeListener(AttributeChangedListener):
        """a very simple class that implements the AttributeChangedListener interface."""

        def on_battery_level_changed(self, battery_level: int) -> None:
            logging.info(f"Battery level changed to: {battery_level}%")

    embody_ble = EmbodyBle()
    embody_ble.connect(sys.argv[1] if len(sys.argv) > 1 else None)
    reporter = EmbodyReporter(embody_ble, BatteryChangeListener())
    reporter.start_battery_level_reporting(int_seconds=2)
    time.sleep(20)
    logging.info("Stop reporting")
    reporter.stop_all_reporting()
    logging.info("Done")
