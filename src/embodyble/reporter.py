"""High level reporter to configure reporting and a callback interface."""

from typing import Optional

from embodycodec import attributes
from embodycodec import codec
from embodycodec import types

from embodyble.embodyble import EmbodyBle

from .attrlistener import AttributeChangedListener
from .attrlistener import AttributeChangedMessageListener


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
            attributes.PulseRawAllAttribute.attribute_id, int_millis, 0x03
        )

    def stop_ecg_ppg_reporting(self) -> None:
        self.__send_reset_reporting(attributes.PulseRawAttribute.attribute_id)
        self.__send_reset_reporting(attributes.PulseRawAllAttribute.attribute_id)

    def stop_all_reporting(self) -> None:
        self.stop_acc_reporting()
        self.stop_afe_settings_reporting()
        self.stop_battery_level_reporting()
        self.stop_belt_on_body_reporting()
        self.stop_breath_rate_reporting()
        self.stop_charge_state_reporting()
        self.stop_diagnostics_reporting()
        self.stop_ecg_ppg_reporting()
        self.stop_firmware_update_reporting()
        self.stop_gyro_reporting()
        self.stop_heart_rate_interval_reporting()
        self.stop_heart_rate_interval_reporting()
        self.stop_heart_rate_reporting()
        self.stop_heart_rate_variability_reporting()
        self.stop_imu_raw_reporting()
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
