"""cli entry point for embodyble.

Parse command line arguments, invoke embody device.
"""
import argparse
import logging
import sys
import time

from embodyserial.helpers import EmbodySendHelper

from . import __version__
from .embodyble import EmbodyBle
from .reporting import AttributeChangedListener
from .reporting import EmbodyReporter


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
    "on_body_state": "get_on_body_state",
}

report_attributes: list[str] = [
    "battery_level",
    "imu",
    "heart_rate",
    "belt_on_body",
    "temperature",
    "heart_rate_variability",
    "heart_rate_interval",
    "charge_state",
    "sleep_mode",
    "recording",
    "leds",
    "firmware_update",
    "afe_settings",
    "single_ecg_ppg",
    "ecg_ppg",
]


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
    embody_ble = EmbodyBle()
    try:
        if parsed_args.list_devices:
            print("Available devices:")
            for device in embody_ble.list_available_devices():
                print(f"\t{device}")
            return
        embody_ble.connect(parsed_args.device)
        send_helper = EmbodySendHelper(sender=embody_ble)

        if parsed_args.get:
            print(f"{getattr(send_helper, get_attributes_dict.get(parsed_args.get))()}")
            return
        elif parsed_args.get_all:
            __get_all_attributes(send_helper)
            return
        elif parsed_args.set_time:
            print(f"Set current time: {send_helper.set_current_timestamp()}")
            print(f"New current time is: {send_helper.get_current_time()}")
            return
        elif parsed_args.set_trace_level:
            print(
                f"Trace level set: {send_helper.set_trace_level(parsed_args.set_trace_level)}"
            )
            return
        elif parsed_args.list_files:
            __list_files(send_helper)
            return
        elif parsed_args.delete_file:
            print(
                f"Delete file {parsed_args.delete_file}:"
                f" {send_helper.delete_file(file_name=parsed_args.delete_file)}"
            )
            return
        elif parsed_args.delete_files:
            print(f"Delete files: {send_helper.delete_all_files()}")
            return
        elif parsed_args.reformat_disk:
            print(f"Reformatting disk: {send_helper.reformat_disk()}")
            return
        elif parsed_args.reset:
            print(f"Resetting device: {send_helper.reset_device()}")
            return
        elif parsed_args.reboot:
            print(f"Rebooting device: {send_helper.reboot_device()}")
            return
        elif parsed_args.activate_on_body_detect:
            print(f"Activating on body detect: {send_helper.set_on_body_detect(True)}")
        elif parsed_args.deactivate_on_body_detect:
            print(
                f"Deactivating on body detect: {send_helper.set_on_body_detect(False)}"
            )
        elif parsed_args.report_attribute:
            attr_changed_listener = AttributeChangedListener()
            reporter = EmbodyReporter(embody_ble, attr_changed_listener)
            # invoke the start_<report_attribute>_reporting method dynamically
            getattr(reporter, f"start_{parsed_args.report_attribute}_reporting")(
                parsed_args.report_interval
            )
            time.sleep(30)
            reporter.stop_all_reporting()
            return
    finally:
        if embody_ble:
            embody_ble.shutdown()


def __get_all_attributes(send_helper: EmbodySendHelper):
    for attrib in get_attributes_dict.keys():
        sys.stdout.write(f"{attrib}: ")
        sys.stdout.flush()
        try:
            method_name = get_attributes_dict.get(attrib)
            if method_name:
                print(getattr(send_helper, method_name)())
        except Exception as e:
            print(f"Error: {e}")


def __list_files(send_helper: EmbodySendHelper):
    files = send_helper.get_files()
    if len(files) > 0:
        for name, size in files:
            print(f"{name} ({round(size/1024)}KB)")
    else:
        print("[]")


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
        default="WARNING",
    )
    parser.add_argument("--device", help="Bluetooth device name", default=None)
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
        "--delete-file", help="Delete specified file", type=str, default=None
    )
    parser.add_argument(
        "--delete-files", help="Delete all files", action="store_true", default=None
    )
    parser.add_argument(
        "--reformat-disk", help="Reformat disk", action="store_true", default=None
    )
    parser.add_argument(
        "--reset", help="Reset device", action="store_true", default=None
    )
    parser.add_argument(
        "--reboot", help="Reboot device", action="store_true", default=None
    )
    parser.add_argument(
        "--report-attribute",
        help="Report selected attribute for 30 seconds (adjust interval with --report-interval)",
        choices=report_attributes,
        default=None,
    )
    parser.add_argument(
        "--report-interval", help="Set report interval", type=int, default=5
    )
    parser.add_argument(
        "--list-devices",
        help="List all available devices",
        action="store_true",
        default=None,
    )
    parser.add_argument(
        "--activate-on-body-detect", help="Activate on body detect", action="store_true"
    )
    parser.add_argument(
        "--deactivate-on-body-detect",
        help="Deactivate on body detect",
        action="store_true",
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
