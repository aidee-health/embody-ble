"""cli entry point for embodyble.

Parse command line arguments, invoke embody device.
"""
import argparse
import logging
import sys

from embodyserial.helpers import EmbodySendHelper

from . import __version__
from .embodyble import EmbodyBle


get_attributes_dict: dict[str, str] = {
    "serialno": "get_serial_no",
    "ble_mac": "get_bluetooth_mac",
    "model": "get_model",
    "vendor": "get_vendor",
    "time": "get_current_time",
    "battery": "get_battery_level",
    "hr": "get_heart_rate",
    "chargestate": "get_charge_state",
    "temperature": "get_temperature",
    "firmware": "get_firmware_version",
}


def main(args=None):
    """Entry point for embody-ble cli.

    The .toml entry_point wraps this in sys.exit already so this effectively
    becomes sys.exit(main()).
    The __main__ entry point similarly wraps sys.exit().
    """
    if args is None:
        args = sys.argv[1:]

    parsed_args = __get_args(args)
    logging.basicConfig(
        level=getattr(logging, parsed_args.log_level.upper(), logging.INFO),
        format="%(asctime)s:%(levelname)s:%(message)s",
    )
    embody_ble = EmbodyBle(device_name=parsed_args.device)
    send_helper = EmbodySendHelper(sender=embody_ble)

    if parsed_args.get:
        logging.info(
            f"{parsed_args.get}: {getattr(send_helper, get_attributes_dict.get(parsed_args.get))()}"
        )
    elif parsed_args.get_all:
        for attrib in get_attributes_dict.keys():
            logging.info(
                f"{attrib}: {getattr(send_helper, get_attributes_dict.get(attrib))()}"
            )
    elif parsed_args.set_time:
        logging.info(f"Set current time: {send_helper.set_current_timestamp()}")
        logging.info(f"New current time is: {send_helper.get_current_time()}")
    elif parsed_args.set_trace_level:
        logging.info(
            f"Trace level set: {send_helper.set_trace_level(parsed_args.set_trace_level)}"
        )
    elif parsed_args.list_files:
        logging.info(f"Files: {send_helper.get_files()}")
    embody_ble.shutdown()


def __get_args(args):
    """Parse arguments passed in from shell."""
    return __get_parser().parse_args(args)


def __get_parser():
    """Return ArgumentParser for pypyr cli."""
    parser = argparse.ArgumentParser(
        allow_abbrev=True,
        description="EmBody CLI application",
        formatter_class=argparse.RawTextHelpFormatter,
    )

    log_levels = ["CRITICAL", "WARNING", "INFO", "DEBUG"]
    parser.add_argument(
        "--log-level",
        help=f"Log level ({log_levels})",
        choices=log_levels,
        default="INFO",
    )
    parser.add_argument(
        "--channel",
        help="Use serial or ble",
        choices=["serial", "ble"],
        default="serial",
    )
    parser.add_argument(
        "--device", help="Device name (serial or ble name)", default=None
    )
    parser.add_argument(
        "--get", help="Get attribute", choices=get_attributes_dict.keys(), default=None
    )
    parser.add_argument(
        "--get-all", help="Get all attributes", action="store_true", default=None
    )
    parser.add_argument(
        "--set-time", help="Set time (to now)", action="store_true", default=None
    )
    parser.add_argument(
        "--set-trace-level", help="Set trace level", type=int, default=None
    )
    parser.add_argument(
        "--list-files",
        help="List all files on device",
        action="store_true",
        default=None,
    )

    parser.add_argument(
        "--version",
        action="version",
        help="Echo version number.",
        version=f"{__version__}",
    )
    return parser


if __name__ == "__main__":
    main()