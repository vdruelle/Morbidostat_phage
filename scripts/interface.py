# Defines the class `interface` with all the hardware relations (which pin is what) and the default functions
# to run the morbidostat. Eventually the low level functions will have to be taken care of with the `asyncio`
# library.

import numpy as np
import time
from hardware_libraries import ADCPi, IOPi


class Interface:
    def __init__(self) -> None:
        "Creates the Interface class"
        self.pumps = []
        self.weight_sensors = []
        self.ODs = []
        self.lights = None
        self.waste_pump = None
        self.vials = np.arange(1,16).tolist()

        self.adc = ADCPi(0x68, 0x69, 16)
        self.adc.set_pga(1)
        self.adc.set_bit_rate(18)

        self.iobus = IOPi(0x20)
        for ii in range(1, 17):  # only outputs
            self.iobus.set_pin_direction(ii, 0)

        self.set_pin_layout()
        self.switch_light(False)

    # --- High level functions ---

    def set_pin_layout(self) -> None:
        "Defines the pins for the pumps, lights etc..."
        self.lights = 1
        self.waste_pump = 2
        self.pumps = np.arange(3, 9).tolist()
        self.ODs = np.arange(1, 5).tolist()
        self.weight_sensors = np.arange(5, 9).tolist()

    def measure_OD(self, vial: int, lag: float = 0.01, nb_measures: int = 1) -> float:
        """Measures the mean OD over nb_measures for the given vial.

        Args:
            vial: vial number.
            lag: delay between measures (in seconds). Defaults to 0.01.
            nb_measures: number of measures. Defaults to 1.

        Returns:
            Mean of the measured ODs.
        """

        values = []
        for ii in range(nb_measures):
            time.sleep(lag)
            OD = self._vial_to_OD(vial)
            values += [self._voltage_to_OD(OD, self._measure_voltage(self._OD_to_pin(vial)))]
        return np.mean(values)

    def inject_volume(self, pump: int, volume: float) -> None:
        """Run the pump to inject a given volume in mL.

        Args:
            pump: pump number
            volume: volume (in mL)
        """
        dt = self._volume_to_time(pump, volume)
        self._run_pump(pump, dt)

    def measure_weight(self, vial: int, lag: float = 0.01, nb_measures: int = 1) -> None:
        """Measures the mean weight (in grams) over nb_measures from given vial.

        Args:
            vial: vial number.
            lag: delay between measures (in second). Defaults to 0.01.
            nb_measures: number of measures. Defaults to 1.

        Returns:
            Mean of the measured weights.
        """

        values = []
        for ii in range(nb_measures):
            time.sleep(lag)
            WS = self._vial_to_weight_sensor(vial)
            values += [self._voltage_to_weight(WS, self._measure_voltage(self._WS_to_pin(vial)))]
        return np.mean(values)

    def remove_waste(self, volume: float) -> None:
        """Runs the waste pump to remove a given volume.

        Args:
            volume: volume (in mL).
        """
        self.iobus.write_pin(self.waste_pump, 1)
        time.sleep(self._volume_to_time(self.waste_pump, volume))
        self.iobus.write_pin(self.waste_pump, 0)

    def wait_mixing(self, dt: float):
        """Wait mixing for a given amount of time.

        Args:
            dt: time (in seconds).
        """
        time.sleep(dt)

    def switch_light(self, state: bool) -> None:
        """Turns lights to the given state. True is on, False is off.

        Args:
            state: True turns lights on, False turns light off.
        """
        assert state in [True, False], f"State {state} is not valid"

        self.iobus.write_pin(self.lights, state)

    # --- Medium level functions ---

    def _volume_to_time(self, pump: int, volume: float) -> float:
        "For now it's useless, just returns 1 second always"
        assert pump in [self.waste_pump] + \
            self.pumps, f"Pump {pump} is not in available pumps: {[self.waste_pump] + self.pumps}"
            
        return volume

    def _voltage_to_OD(self, OD: int, voltage: float) -> float:
        "For now this useless, just returns the raw voltage"
        assert OD in self.ODs, f"OD {OD} is not in available ODs: {self.ODs}"

        return voltage

    def _voltage_to_weight(self, weight_sensor: int, voltage: float) -> float:
        "For now this is useless, just returns the raw voltage"
        assert weight_sensor in self.weight_sensor, \
            f"weight_sensors {weight_sensor} is not in available weight sensors: {self.weight_sensors}"

        return voltage

    def _run_pump(self, pump: int, dt: float) -> None:
        """Run the pump for a given amount of time. Used for all pumps except waste pump.

        Args:
            pump: pump number
            dt: duration
        """
        
        self.iobus.write_pin(self._pump_to_pin(pump), 1)
        time.sleep(dt)
        self.iobus.write_pin(self._pump_to_pin(pump), 0)

    # --- Low level functions ---

    def _pump_to_pin(self, pump_number: int) -> int:
        """Return the pin number associated to the pump number.

        Args:
            pump_number: number associated to the pump

        Returns:
            pin associated to the pump
        """
        assert pump_number in self.pumps, f"Pump {pump_number} is not in available pumps: {self.pumps}"

        return self.pumps[pump_number - 1]

    def _WS_to_pin(self, vial_number: int) -> int:
        """Returns the ADCpi pin associated to the vial weight sensor.

        Args:
            vial_number: number associated to the vial.

        Returns:
            ADCpi pin associated to the weight sensor.
        """
        assert vial_number in self.vials, f"Vial, {vial_number} is not in the available vials: {self.vials}"

        return self.weight_sensors[vial_number - 1]

    def _OD_to_pin(self, vial_number: int) -> int:
        """Returns the ADCpi pin associated to the vial phototransistor.

        Args:
            vial_number: number associated to the vial.

        Returns:
            ADCpi pin associated to the phototransistor.
        """
        assert vial_number in self.vials, f"Vial, {vial_number} is not in the available vials: {self.vials}"

        return self.ODs[vial_number - 1]

    def _vial_to_OD(self, vial_number: int) -> int:
        """Returns the OD number associated to the vial number.

        Args:
            vial_number: number associated to the vial.

        Returns:
            OD number associated to the vial.
        """
        assert vial_number in self.vials, f"Vial, {vial_number} is not in the available vials: {self.vials}"

        return self.ODs[vial_number - 1]

    def _vial_to_weight_sensor(self, vial_number: int) -> int:
        """Returns the weight sensor number associated to the vial number.

        Args:
            vial_number: number associated to the vial.

        Returns:
            Weight sensor number associated to the vial.
        """
        assert vial_number in self.vials, f"Vial, {vial_number} is not in the available vials: {self.vials}"

        return self.weight_sensors[vial_number - 1]

    def _measure_voltage(self, adc_pin: int) -> float:
        """Measures voltage from the given pin.

        Args:
            adc_pin: pin number.

        Returns:
            Voltage as measures by the ADCpi.
        """
        assert (
            adc_pin in self.weight_sensors) or (
            adc_pin in self.ODs), f"ADC pin {adc_pin} isn't in defined WS and ODs"

        return self.adc.read_voltage(adc_pin)


if __name__ == "__main__":
    tmp = Interface()
