"""This module provides a reporter wrapper along with a high level listener interface."""

import logging
import struct
from datetime import datetime
from datetime import timezone
from typing import Optional

from embodycodec import attributes
from embodycodec import codec
from embodycodec import types

from embodyble.embodyble import EmbodyBle
from embodyble.listeners import BleMessageListener
from embodyble.listeners import MessageListener


SYSTEM_ID_UUID = "00002A23-0000-1000-8000-00805f9b34fb"
MODEL_NBR_UUID = "00002A24-0000-1000-8000-00805f9b34fb"
DEVICE_NAME_UUID = "00002A00-0000-1000-8000-00805f9b34fb"
SERIAL_NO_UUID = "00002A25-0000-1000-8000-00805f9b34fb"
FIRMWARE_REV_UUID = "00002A26-0000-1000-8000-00805f9b34fb"
HARDWARE_REV_UUID = "00002A27-0000-1000-8000-00805f9b34fb"
SOFTWARE_REV_UUID = "00002A28-0000-1000-8000-00805f9b34fb"
MANUFACTURER_NAME_UUID = "00002A29-0000-1000-8000-00805f9b34fb"
CURRENT_TIME_UUID = "00002A2B-0000-1000-8000-00805f9b34fb"
BATTERY_LEVEL_UUID = "00002A19-0000-1000-8000-00805f9b34fb"


class AttributeChangedListener:
    """High level listener interface for being notified of attribute changed messages.

    Override the methods you are interested in.
    """

    def on_battery_level_changed(self, battery_level: int) -> None:
        logging.info(f"Battery level changed: {battery_level}%")

    def on_imu_changed(self, orientation: int, activity_level: int) -> None:
        logging.info(
            f"IMU changed: orientation={orientation}, activity_level={activity_level}"
        )

    def on_belt_on_body_changed(self, belt_on_body: bool) -> None:
        logging.info(f"Belt on body changed: {belt_on_body}")

    def on_breathing_rate_changed(self, breathing_rate: int) -> None:
        logging.info(f"Breathing rate changed: {breathing_rate}")

    def on_heart_rate_variability_changed(self, heart_rate_variability: int) -> None:
        logging.info(f"Heart rate variability changed: {heart_rate_variability}")

    def on_heart_rate_changed(self, heart_rate: int) -> None:
        logging.info(f"Heart rate changed: {heart_rate}")

    def on_heartrate_interval_changed(self, heartrate_interval: int) -> None:
        logging.info(f"Heart rate interval changed: {heartrate_interval}")

    def on_charge_state_changed(self, charge_state: bool) -> None:
        logging.info(f"Charge state changed: {charge_state}")

    def on_sleep_mode_changed(self, sleep_mode: int) -> None:
        logging.info(f"Sleep mode changed: {sleep_mode}")

    def on_imu_raw_changed(
        self, acc_x: int, acc_y: int, acc_z: int, gyr_x: int, gyr_y: int, gyr_z: int
    ) -> None:
        logging.info(
            f"IMU raw changed: acc_x={acc_x}, acc_y={acc_y}, acc_z={acc_z}, gyr_x={gyr_x}, gyr_y={gyr_y}, gyr_z={gyr_z}"
        )

    def on_acc_changed(self, acc_x: int, acc_y: int, acc_z: int) -> None:
        logging.info(f"Acc changed: acc_x={acc_x}, acc_y={acc_y}, acc_z={acc_z}")

    def on_gyr_changed(self, gyr_x: int, gyr_y: int, gyr_z: int) -> None:
        logging.info(f"Gyr changed: gyr_x={gyr_x}, gyr_y={gyr_y}, gyr_z={gyr_z}")

    def on_recording_changed(self, recording: bool) -> None:
        logging.info(f"Recording changed: {recording}")

    def on_temperature_changed(self, temperature: float) -> None:
        logging.info(f"Temperature changed: {temperature}")

    def on_leds_changed(
        self,
        led1: bool,
        led1_blinking: bool,
        led2: bool,
        led2_blinking: bool,
        led3: bool,
        led3_blinking: bool,
    ) -> None:
        logging.info(
            f"LEDs changed: L1={led1}, L1_blink={led1_blinking}, L2={led2}, "
            f"L2_blink={led2_blinking}, L3={led3}, L3_blink={led3_blinking}"
        )

    def on_firmware_update_changed(self, firmware_update: int) -> None:
        logging.info(f"Firmware update changed: {firmware_update}")

    def on_diagnostics_changed(
        self,
        rep_soc: int,
        avg_current: int,
        rep_cap: int,
        full_cap: int,
        tte: int,
        ttf: int,
        voltage: int,
        avg_voltage: int,
    ) -> None:
        logging.info(
            f"Diagnostics changed: rep_soc={rep_soc}, avg_current={avg_current}, "
            f"rep_cap={rep_cap}, full_cap={full_cap}, tte={tte}, ttf={ttf}, "
            f"voltage={voltage}, avg_voltage={avg_voltage}"
        )

    def on_afe_settings_changed(
        self,
        rf_gain: int,
        cf_value: int,
        ecg_gain: int,
        ioffdac_range: int,
        led1: int,
        led4: int,
        off_dac1: int,
        relative_gain: float,
        led2: Optional[int],
        led3: Optional[int],
        off_dac2: Optional[int],
        off_dac3: Optional[int],
    ) -> None:
        logging.info(
            f"AFE settings changed: rf_gain={rf_gain}, cf_value={cf_value}, ecg_gain={ecg_gain}, "
            f"ioffdac_range={ioffdac_range}, led1={led1}, led2={led2}, led3={led3}, led4={led4}, "
            f"off_dac1={off_dac1}, off_dac2={off_dac2}, off_dac3={off_dac3}, relative_gain={relative_gain}"
        )

    def on_ecgs_ppgs_changed(self, ecgs: list[int], ppgs: list[int]) -> None:
        logging.info(f"ECGs and PPGs changed: ecgs={ecgs}, ppgs={ppgs}")

    def on_on_body_detection_changed(self, on_body_detection: bool) -> None:
        logging.info(
            f"On body detection {'activated' if on_body_detection else 'deactivated'}"
        )


class AttributeChangedMessageListener(MessageListener, BleMessageListener):
    """MessageListener implementation delegating to high level callback interface."""

    def __init__(
        self, attr_changed_listener: Optional[AttributeChangedListener] = None
    ) -> None:
        self.__message_listeners: list[AttributeChangedListener] = []
        if attr_changed_listener is not None:
            self.add_attr_changed_listener(attr_changed_listener)

    def add_attr_changed_listener(self, listener: AttributeChangedListener) -> None:
        self.__message_listeners.append(listener)

    def message_received(self, msg: codec.Message) -> None:
        """Process received message and delegate to listener callback."""
        if isinstance(msg, codec.AttributeChanged):
            if isinstance(msg.value, attributes.BatteryLevelAttribute):
                for listener in self.__message_listeners:
                    listener.on_battery_level_changed(msg.value.value)
            elif isinstance(msg.value, attributes.ImuAttribute):
                for listener in self.__message_listeners:
                    listener.on_imu_changed(
                        msg.value.value.orientation_and_activity & 0xF0,
                        msg.value.value.orientation_and_activity & 0x0F,
                    )
            elif isinstance(msg.value, attributes.BeltOnBodyStateAttribute):
                for listener in self.__message_listeners:
                    listener.on_belt_on_body_changed(msg.value.value)
            elif isinstance(msg.value, attributes.BreathRateAttribute):
                for listener in self.__message_listeners:
                    listener.on_breathing_rate_changed(msg.value.value)
            elif isinstance(msg.value, attributes.HeartRateVariabilityAttribute):
                for listener in self.__message_listeners:
                    listener.on_heart_rate_variability_changed(msg.value.value)
            elif isinstance(msg.value, attributes.HeartrateAttribute):
                for listener in self.__message_listeners:
                    listener.on_heart_rate_changed(msg.value.value)
            elif isinstance(msg.value, attributes.HeartRateIntervalAttribute):
                for listener in self.__message_listeners:
                    listener.on_heartrate_interval_changed(msg.value.value)
            elif isinstance(msg.value, attributes.ChargeStateAttribute):
                for listener in self.__message_listeners:
                    listener.on_charge_state_changed(msg.value.value)
            elif isinstance(msg.value, attributes.SleepModeAttribute):
                for listener in self.__message_listeners:
                    listener.on_sleep_mode_changed(msg.value.value)
            elif isinstance(msg.value, attributes.ImuRawAttribute):
                for listener in self.__message_listeners:
                    listener.on_imu_raw_changed(
                        msg.value.value.acc_x,
                        msg.value.value.acc_y,
                        msg.value.value.acc_z,
                        msg.value.value.gyr_x,
                        msg.value.value.gyr_y,
                        msg.value.value.gyr_z,
                    )
            elif isinstance(msg.value, attributes.AccRawAttribute):
                for listener in self.__message_listeners:
                    listener.on_acc_changed(
                        msg.value.value.acc_x,
                        msg.value.value.acc_y,
                        msg.value.value.acc_z,
                    )
            elif isinstance(msg.value, attributes.GyroRawAttribute):
                for listener in self.__message_listeners:
                    listener.on_gyr_changed(
                        msg.value.value.gyr_x,
                        msg.value.value.gyr_y,
                        msg.value.value.gyr_z,
                    )
            elif isinstance(msg.value, attributes.MeasurementDeactivatedAttribute):
                for listener in self.__message_listeners:
                    listener.on_recording_changed(msg.value.value > 0)
            elif isinstance(msg.value, attributes.TemperatureAttribute):
                for listener in self.__message_listeners:
                    listener.on_temperature_changed(msg.value.temp_celsius())
            elif isinstance(msg.value, attributes.LedsAttribute):
                for listener in self.__message_listeners:
                    listener.on_leds_changed(
                        msg.value.led1(),
                        msg.value.led1_blinking(),
                        msg.value.led2(),
                        msg.value.led2_blinking(),
                        msg.value.led3(),
                        msg.value.led3_blinking(),
                    )
            elif isinstance(msg.value, attributes.FirmwareUpdateProgressAttribute):
                for listener in self.__message_listeners:
                    listener.on_firmware_update_changed(msg.value.value)
            elif isinstance(msg.value, attributes.OnBodyDetectAttribute):
                for listener in self.__message_listeners:
                    listener.on_on_body_detection_changed(msg.value.value)
            elif isinstance(msg.value, attributes.DiagnosticsAttribute):
                for listener in self.__message_listeners:
                    listener.on_diagnostics_changed(
                        msg.value.value.rep_soc,
                        msg.value.value.avg_current,
                        msg.value.value.rep_cap,
                        msg.value.value.full_cap,
                        msg.value.value.tte,
                        msg.value.value.ttf,
                        msg.value.value.voltage,
                        msg.value.value.avg_voltage,
                    )
            elif isinstance(msg.value, attributes.AfeSettingsAttribute):
                for listener in self.__message_listeners:
                    listener.on_afe_settings_changed(
                        msg.value.value.rf_gain,
                        msg.value.value.cf_value,
                        msg.value.value.ecg_gain,
                        msg.value.value.ioffdac_range,
                        msg.value.value.led1,
                        msg.value.value.led4,
                        msg.value.value.off_dac,
                        msg.value.value.relative_gain,
                        None,
                        None,
                        None,
                        None,
                    )
            elif isinstance(msg.value, attributes.AfeSettingsAllAttribute):
                for listener in self.__message_listeners:
                    listener.on_afe_settings_changed(
                        msg.value.value.rf_gain if msg.value.value.rf_gain else 0,
                        msg.value.value.cf_value if msg.value.value.cf_value else 0,
                        msg.value.value.ecg_gain if msg.value.value.ecg_gain else 0,
                        msg.value.value.ioffdac_range
                        if msg.value.value.ioffdac_range
                        else 0,
                        msg.value.value.led1 if msg.value.value.led1 else 0,
                        msg.value.value.led4 if msg.value.value.led4 else 0,
                        msg.value.value.off_dac1 if msg.value.value.off_dac1 else 0,
                        msg.value.value.relative_gain
                        if msg.value.value.relative_gain
                        else 0,
                        msg.value.value.led2,
                        msg.value.value.led3,
                        msg.value.value.off_dac2,
                        msg.value.value.off_dac3,
                    )
            else:
                logging.warning("Unhandled attribute changed message: %s", msg)
        elif isinstance(msg, codec.RawPulseChanged):
            if isinstance(msg.value, attributes.PulseRawAttribute):
                for listener in self.__message_listeners:
                    listener.on_ecgs_ppgs_changed(
                        [msg.value.value.ecg], [msg.value.value.ppg]
                    )
            elif isinstance(msg.value, attributes.PulseRawAllAttribute):
                for listener in self.__message_listeners:
                    listener.on_ecgs_ppgs_changed(
                        [msg.value.ecg],
                        [
                            msg.value.value.ppg_green,
                            msg.value.value.ppg_red,
                            msg.value.value.ppg_ir,
                        ],
                    )
        elif isinstance(msg, codec.RawPulseListChanged):
            for listener in self.__message_listeners:
                listener.on_ecgs_ppgs_changed(
                    msg.value.value.ecgs, msg.value.value.ppgs
                )
        else:
            logging.warning("Unhandled message: %s", msg)

    def ble_message_received(self, uuid: str, data: bytes) -> None:
        """Process received message"""
        if uuid == BATTERY_LEVEL_UUID:
            for listener in self.__message_listeners:
                listener.on_battery_level_changed(int(data))


class EmbodyReporter:
    """Reporter class to configure embody reporting and a callback interface.

    Note! Setting interval to 0 means sending on all changes.
    """

    def __init__(
        self,
        embody_ble: EmbodyBle,
        attr_changed_listener: Optional[AttributeChangedListener] = None,
    ) -> None:
        self.__embody_ble = embody_ble
        self.__attribute_changed_message_listener = AttributeChangedMessageListener(
            attr_changed_listener=attr_changed_listener
        )
        self.__embody_ble.add_message_listener(
            self.__attribute_changed_message_listener
        )
        self.__embody_ble.add_ble_message_listener(
            self.__attribute_changed_message_listener
        )

    def add_attribute_changed_listener(
        self, attr_changed_listener: AttributeChangedListener
    ) -> None:
        self.__attribute_changed_message_listener.add_attr_changed_listener(
            attr_changed_listener
        )

    def start_battery_level_reporting(self, int_seconds: int) -> None:
        self.__send_configure_reporting(
            attributes.BatteryLevelAttribute.attribute_id, int_seconds
        )

    def stop_battery_level_reporting(self) -> None:
        self.__send_reset_reporting(attributes.BatteryLevelAttribute.attribute_id)

    def start_imu_reporting(self, int_millis: int) -> None:
        self.__send_configure_reporting(
            attributes.ImuAttribute.attribute_id, int_millis
        )

    def stop_imu_reporting(self) -> None:
        self.__send_reset_reporting(attributes.ImuAttribute.attribute_id)

    def start_belt_on_body_reporting(self, int_millis: int = 0) -> None:
        self.__send_configure_reporting(
            attributes.BeltOnBodyStateAttribute.attribute_id, int_millis
        )

    def stop_belt_on_body_reporting(self) -> None:
        self.__send_reset_reporting(attributes.BeltOnBodyStateAttribute.attribute_id)

    def start_breath_rate_reporting(self, int_millis: int) -> None:
        self.__send_configure_reporting(
            attributes.BreathRateAttribute.attribute_id, int_millis
        )

    def stop_breath_rate_reporting(self) -> None:
        self.__send_reset_reporting(attributes.BreathRateAttribute.attribute_id)

    def start_heart_rate_variability_reporting(self, int_millis: int) -> None:
        self.__send_configure_reporting(
            attributes.HeartRateVariabilityAttribute.attribute_id, int_millis
        )

    def stop_heart_rate_variability_reporting(self) -> None:
        self.__send_reset_reporting(
            attributes.HeartRateVariabilityAttribute.attribute_id
        )

    def start_heart_rate_reporting(self, int_millis: int = 0) -> None:
        self.__send_configure_reporting(
            attributes.HeartrateAttribute.attribute_id, int_millis
        )

    def stop_heart_rate_reporting(self) -> None:
        self.__send_reset_reporting(attributes.HeartrateAttribute.attribute_id)

    def start_heart_rate_interval_reporting(self, int_millis: int = 0) -> None:
        self.__send_configure_reporting(
            attributes.HeartRateIntervalAttribute.attribute_id, int_millis
        )

    def stop_heart_rate_interval_reporting(self) -> None:
        self.__send_reset_reporting(attributes.HeartRateIntervalAttribute.attribute_id)

    def start_charge_state_reporting(self, int_seconds: int = 0) -> None:
        self.__send_configure_reporting(
            attributes.ChargeStateAttribute.attribute_id, int_seconds
        )

    def stop_charge_state_reporting(self) -> None:
        self.__send_reset_reporting(attributes.ChargeStateAttribute.attribute_id)

    def start_sleep_mode_reporting(self, int_seconds: int = 0) -> None:
        self.__send_configure_reporting(
            attributes.SleepModeAttribute.attribute_id, int_seconds
        )

    def stop_sleep_mode_reporting(self) -> None:
        self.__send_reset_reporting(attributes.SleepModeAttribute.attribute_id)

    def start_imu_raw_reporting(self, int_millis: int) -> None:
        raise Exception("Not supported over BLE by EmBody yet")

    def stop_imu_raw_reporting(self) -> None:
        self.__send_reset_reporting(attributes.ImuRawAttribute.attribute_id)

    def start_acc_reporting(self, int_millis: int) -> None:
        raise Exception("Not supported over BLE by EmBody yet. Only reports to file")

    def stop_acc_reporting(self) -> None:
        self.__send_reset_reporting(attributes.AccRawAttribute.attribute_id)

    def start_gyro_reporting(self, int_millis: int) -> None:
        raise Exception("Not supported over BLE by EmBody yet. Only reports to file")

    def stop_gyro_reporting(self) -> None:
        self.__send_reset_reporting(attributes.GyroRawAttribute.attribute_id)

    def start_recording_reporting(self) -> None:
        self.__send_configure_reporting(
            attributes.MeasurementDeactivatedAttribute.attribute_id, 0
        )

    def stop_recording_reporting(self) -> None:
        self.__send_reset_reporting(
            attributes.MeasurementDeactivatedAttribute.attribute_id
        )

    def start_temperature_reporting(self, int_seconds: int) -> None:
        self.__send_configure_reporting(
            attributes.TemperatureAttribute.attribute_id, int_seconds
        )

    def stop_temperature_reporting(self) -> None:
        self.__send_reset_reporting(attributes.TemperatureAttribute.attribute_id)

    def start_leds_reporting(self, int_millis: int) -> None:
        self.__send_configure_reporting(
            attributes.LedsAttribute.attribute_id, int_millis
        )

    def stop_leds_reporting(self) -> None:
        self.__send_reset_reporting(attributes.LedsAttribute.attribute_id)

    def start_firmware_update_reporting(self, int_seconds: int) -> None:
        self.__send_configure_reporting(
            attributes.FirmwareUpdateProgressAttribute.attribute_id, int_seconds
        )

    def stop_firmware_update_reporting(self) -> None:
        self.__send_reset_reporting(
            attributes.FirmwareUpdateProgressAttribute.attribute_id
        )

    def start_diagnostics_reporting(self, int_millis: int) -> None:
        self.__send_configure_reporting(
            attributes.DiagnosticsAttribute.attribute_id, int_millis
        )

    def stop_diagnostics_reporting(self) -> None:
        self.__send_reset_reporting(attributes.DiagnosticsAttribute.attribute_id)

    def start_afe_settings_reporting(self, int_millis: int) -> None:
        self.__send_configure_reporting(
            attributes.AfeSettingsAllAttribute.attribute_id, int_millis
        )

    def stop_afe_settings_reporting(self) -> None:
        self.__send_reset_reporting(attributes.AfeSettingsAllAttribute.attribute_id)

    def start_single_ecg_ppg_reporting(self, int_millis: int) -> None:
        self.__send_configure_reporting(
            attributes.PulseRawAttribute.attribute_id, int_millis
        )

    def start_ecg_ppg_reporting(self, int_millis: int) -> None:
        self.__send_configure_reporting(
            attributes.PulseRawAllAttribute.attribute_id, int_millis
        )

    def stop_ecg_ppg_reporting(self) -> None:
        self.__send_reset_reporting(attributes.PulseRawAttribute.attribute_id)
        self.__send_reset_reporting(attributes.PulseRawAllAttribute.attribute_id)

    def stop_all_reporting(self) -> None:
        # self.stop_acc_reporting()
        self.stop_afe_settings_reporting()
        self.stop_battery_level_reporting()
        self.stop_belt_on_body_reporting()
        self.stop_breath_rate_reporting()
        self.stop_charge_state_reporting()
        self.stop_diagnostics_reporting()
        self.stop_ecg_ppg_reporting()
        self.stop_firmware_update_reporting()
        # self.stop_gyro_reporting()
        self.stop_heart_rate_interval_reporting()
        self.stop_heart_rate_interval_reporting()
        self.stop_heart_rate_reporting()
        self.stop_heart_rate_variability_reporting()
        # self.stop_imu_raw_reporting()
        self.stop_imu_reporting()
        self.stop_leds_reporting()
        self.stop_recording_reporting()
        self.stop_sleep_mode_reporting()
        self.stop_temperature_reporting()

    def __send_configure_reporting(
        self, attribute_id: int, interval: int, reporting_mode: int = 0x01
    ) -> None:
        self.__embody_ble.send(
            codec.ConfigureReporting(
                attribute_id,
                types.Reporting(interval=interval, on_change=reporting_mode),
            )
        )

    def __send_reset_reporting(self, attribute_id: int) -> None:
        self.__embody_ble.send(codec.ResetReporting(attribute_id))

    # BLE specific methods ###

    def read_ble_manufacturer_name(self) -> str:
        manufacturer_name = self.__embody_ble.request_ble_attribute(
            MANUFACTURER_NAME_UUID
        )
        return str(manufacturer_name, "ascii")

    def read_ble_serial_no(self) -> str:
        serial_no = self.__embody_ble.request_ble_attribute(SERIAL_NO_UUID)
        return str(serial_no, "ascii")

    def read_ble_software_revision(self) -> str:
        software_revision = self.__embody_ble.request_ble_attribute(SOFTWARE_REV_UUID)
        return str(software_revision, "ascii")

    def read_ble_battery_level(self) -> int:
        battery_level = self.__embody_ble.request_ble_attribute(BATTERY_LEVEL_UUID)
        return int.from_bytes(battery_level, byteorder="big")

    def read_ble_current_time(self) -> datetime:
        current_time = self.__embody_ble.request_ble_attribute(CURRENT_TIME_UUID)
        return convert_from_gatt_current_time(current_time)

    def write_ble_current_time(self, timestamp: datetime) -> None:
        self.__embody_ble.write_ble_attribute(
            CURRENT_TIME_UUID, convert_to_gatt_current_time(timestamp)
        )

    def start_ble_battery_level_reporting(self) -> None:
        self.__embody_ble.start_ble_notify(BATTERY_LEVEL_UUID)

    def stop_ble_battery_level_reporting(self) -> None:
        self.__embody_ble.stop_ble_notify(BATTERY_LEVEL_UUID)


def convert_to_gatt_current_time(timestamp: datetime) -> bytes:
    """Accessory function to convert a datetime object to a GATT current time byte array."""
    dt = timestamp.astimezone(timezone.utc)
    return struct.pack(
        "<hbbbbb", dt.year, dt.month, dt.day, dt.hour, dt.minute, dt.second
    )


def convert_from_gatt_current_time(time_bytes: bytes) -> datetime:
    """Accessory function to convert a GATT current time byte array to a datetime object."""
    year, month, day, hour, minute, second = struct.unpack("<hbbbbb", time_bytes[0:7])
    return datetime(year, month, day, hour, minute, second, tzinfo=timezone.utc)
