"""High level listener implementation with a high level callback interface."""

import logging
from typing import Optional

from embodycodec import attributes
from embodycodec import codec

from .listeners import MessageListener


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
            f"LEDs changed: L1={led1}, L1_blink={led1_blinking}, L2={led2}, \
            L2_blink={led2_blinking}, L3={led3}, L3_blink={led3_blinking}"
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
            f"Diagnostics changed: rep_soc={rep_soc}, avg_current={avg_current}\
                , rep_cap={rep_cap}, full_cap={full_cap}, tte={tte}, ttf={ttf}, \
                voltage={voltage}, avg_voltage={avg_voltage}"
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
            f"AFE settings changed: rf_gain={rf_gain}, cf_value={cf_value}, ecg_gain={ecg_gain}, \
                ioffdac_range={ioffdac_range}, led1={led1}, led2={led2}, led3={led3}, led4={led4},\
                    off_dac1={off_dac1}, off_dac2={off_dac2}, off_dac3={off_dac3}, relative_gain={relative_gain}"
        )

    def on_ecgs_ppgs_changed(self, ecgs: list[int], ppgs: list[int]) -> None:
        logging.info(f"ECGs and PPGs changed: ecgs={ecgs}, ppgs={ppgs}")


class AttributeChangedMessageListener(MessageListener):
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
                        msg.value.orientation_and_activity & 0xF0,
                        msg.value.activity_level & 0x0F,
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
                        msg.value.acc_x,
                        msg.value.acc_y,
                        msg.value.acc_z,
                        msg.value.gyr_x,
                        msg.value.gyr_y,
                        msg.value.gyr_z,
                    )
            elif isinstance(msg.value, attributes.AccRawAttribute):
                for listener in self.__message_listeners:
                    listener.on_acc_changed(
                        msg.value.acc_x, msg.value.acc_y, msg.value.acc_z
                    )
            elif isinstance(msg.value, attributes.GyroRawAttribute):
                for listener in self.__message_listeners:
                    listener.on_gyr_changed(
                        msg.value.gyr_x, msg.value.gyr_y, msg.value.gyr_z
                    )
            elif isinstance(msg.value, attributes.MeasurementDeactivatedAttribute):
                for listener in self.__message_listeners:
                    listener.on_recording_changed(msg.value.value != 0)
            elif isinstance(msg.value, attributes.TemperatureAttribute):
                for listener in self.__message_listeners:
                    listener.on_temperature_changed(msg.value.value)
            elif isinstance(msg.value, attributes.LedsAttribute):
                for listener in self.__message_listeners:
                    listener.on_leds_changed(
                        msg.value.led1,
                        msg.value.led1_blinking,
                        msg.value.led2,
                        msg.value.led2_blinking,
                        msg.value.led3,
                        msg.value.led3_blinking,
                    )
            elif isinstance(msg.value, attributes.FirmwareUpdateProgressAttribute):
                for listener in self.__message_listeners:
                    listener.on_firmware_update_changed(msg.value.value)
            elif isinstance(msg.value, attributes.DiagnosticsAttribute):
                for listener in self.__message_listeners:
                    listener.on_diagnostics_changed(
                        msg.value.rep_soc,
                        msg.value.avg_current,
                        msg.value.rep_cap,
                        msg.value.full_cap,
                        msg.value.tte,
                        msg.value.ttf,
                        msg.value.voltage,
                        msg.value.avg_voltage,
                    )
            elif isinstance(msg.value, attributes.AfeSettingsAttribute):
                for listener in self.__message_listeners:
                    listener.on_afe_settings_changed(
                        msg.value.rf_gain,
                        msg.value.cf_value,
                        msg.value.ecg_gain,
                        msg.value.ioffdac_range,
                        msg.value.led1,
                        msg.value.led4,
                        msg.value.off_dac,
                        msg.value.relative_gain,
                    )
            elif isinstance(msg.value, attributes.AfeSettingsAllAttribute):
                for listener in self.__message_listeners:
                    listener.on_afe_settings_changed(
                        msg.value.rf_gain,
                        msg.value.cf_value,
                        msg.value.ecg_gain,
                        msg.value.ioffdac_range,
                        msg.value.led1,
                        msg.value.led4,
                        msg.value.off_dac1,
                        msg.value.relative_gain,
                        msg.value.led2,
                        msg.value.led3,
                        msg.value.off_dac2,
                        msg.value.off_dac3,
                    )
            else:
                logging.warning("Unhandled attribute changed message: %s", msg)
        elif isinstance(msg, codec.RawPulseChanged):
            if isinstance(msg.value, attributes.PulseRawAttribute):
                for listener in self.__message_listeners:
                    listener.on_raw_pulse_changed([msg.value.ecg], [msg.value.ppg])
            elif isinstance(msg.value, attributes.PulseRawAllAttribute):
                for listener in self.__message_listeners:
                    listener.on_raw_pulse_changed(
                        [msg.value.ecg],
                        [msg.value.ppg_green, msg.value.ppg_red, msg.value.ppg_ir],
                    )
        elif isinstance(msg, codec.RawPulseListChanged):
            for listener in self.__message_listeners:
                listener.on_raw_pulse_changed(msg.value.ecgs, msg.value.ppgs)
        else:
            logging.warning("Unhandled message: %s", msg)
