# Defines the class `interface` with all the hardware relations (which pin is what) and the default functions
# to run the morbidostat. Eventually the low level functions will have to be taken care of with the `asyncio`
# library.

import numpy as np
import time
import yaml
from hardware_libraries import ADCPi, IOPi


class Interface:
    def __init__(self) -> None:
        "Creates the Interface class"
        self.pumps = []  # self.pumps[1] gives you the pin corresponding to the first pump
        self.weight_sensors = []  # self.weight_sensors[1] gives you the pin corresponding to the first WS
        self.ODs = []
        self.lights = None
        self.waste_pump = None
        self.vials = None

        self.calibration = None

        self.adc = ADCPi(0x68, 0x69, 16)
        self.adc.set_pga(1)
        self.adc.set_bit_rate(18)

        self.iobus = IOPi(0x20)
        for ii in range(1, 17):  # only outputs
            self.iobus.set_pin_direction(ii, 0)

        self.set_hardware_connections()
        self.load_calibration("03-21-15h-06min.yaml")
        self.turn_off()

    # --- Hardware setup ---

    def set_hardware_connections(self) -> None:
        """This function defines the physical connection from the different components to the pin of the RPi.
        """
        self.vials = list(range(1, 3))
        self.lights = 1
        self.waste_pump = 2
        self.pumps = list(range(3, 9))
        self.ODs = list(range(1, 5))
        self.weight_sensors = list(range(5, 9))

    def load_calibration(self, file) -> None:
        """Load the calibration file, process it and saves it in the Interface class.

        Args:
            file: calibration file name including extension (ex: '03-21-15h-06min.yaml').
        """

        # Opening file as a dictionary
        with open("calibrations/" + file, 'r') as stream:
            self.calibration = yaml.load(stream, Loader=yaml.loader.BaseLoader)

        # Converting values from string to floats
        for key1 in self.calibration.keys():
            for key2 in self.calibration[key1].keys():
                for key3 in self.calibration[key1][key2].keys():
                    self.calibration[key1][key2][key3]["value"] = float(self.calibration[key1][key2][key3]["value"])


    # --- High level functions ---

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
            values += [self._voltage_to_OD(vial, self._measure_voltage(self._OD_to_pin(vial)))]
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
            values += [self._voltage_to_weight(vial, self._measure_voltage(self._WS_to_pin(vial)))]
        return np.mean(values)

    def remove_waste(self, volume: float) -> None:
        """Runs the waste pump to remove a given volume.

        Args:
            volume: volume (in mL).
        """
        self.iobus.write_pin(self.waste_pump, 1)
        time.sleep(volume)
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

    def turn_off(self) -> None:
        """Turns everything controlled by the interface to off state.
        """
        for pump in range(1, len(self.pumps) + 1):
            self.iobus.write_pin(self._pump_to_pin(pump), 0)
        self.switch_light(False)
        self.iobus.write_pin(self.waste_pump, 0)


    # --- Medium level functions ---

    def _volume_to_time(self, pump: int, volume: float) -> float:
        """Uses the calibration of the pump to convert a volume in mL to a pumping duration in seconds.

        Args:
            pump: pump number.
            volume: volume to pump in mL.

        Returns:
            t: time (in seconds) to pump the given volume.
        """
        available_pumps = list(range(1, len(self.pumps) + 1))
        assert pump in available_pumps, f"Pump {pump} is not in the available pumps {available_pumps}"

        t = volume/self.calibration["pumps"][f"pump {pump}"]["value"]
        return t

    def _voltage_to_OD(self, vial: int, voltage: float) -> float:
        """Uses the calibration to convert the voltage measured to an OD value.

        Args:
            vial: vial number.
            voltage: voltage measured in Volts.

        Returns:
            OD: OD600 corresponding to the voltage measured for the given vial.
        """
        assert vial in self.vials, f"Vial {vial} is not in the available vials: {self.vials}"

        slope = self.calibration["OD"][f"vial {vial}"]["slope"]["value"]
        intercept = self.calibration["OD"][f"vial {vial}"]["intercept"]["value"]
        OD = (voltage - intercept) / slope

        return OD

    def _voltage_to_weight(self, vial: int, voltage: float) -> float:
        """Uses the calibration to convert the voltage measure to an weight in grams.

        Args:
            vial: vial number.
            voltage: voltage measured in Volts.

        Returns:
            weight: weight in grams corresponding to the voltage measured for the given vial.
        """
        assert vial in self.vials, f"Vial {vial} is not in the available vials: {self.vials}"

        slope = self.calibration["WS"][f"vial {vial}"]["slope"]["value"]
        intercept = self.calibration["WS"][f"vial {vial}"]["intercept"]["value"]
        weight = (voltage - intercept) / slope

        return weight

    def _run_pump(self, pump: int, dt: float) -> None:
        """Run the pump for a given amount of time. Used for all pumps except waste pump.

        Args:
            pump: pump number.
            dt: duration in seconds.
        """

        self.iobus.write_pin(self._pump_to_pin(pump), 1)
        time.sleep(dt)
        self.iobus.write_pin(self._pump_to_pin(pump), 0)

    # --- Low level functions ---

    def _pump_to_pin(self, pump: int) -> int:
        """Return the pin number associated to the pump number.

        Args:
            pump: number associated to the pump

        Returns:
            pin associated to the pump
        """
        available_pumps = list(range(1, len(self.pumps) + 1))
        assert pump in available_pumps, f"Pump {pump} is not in the available pumps {available_pumps}"

        return self.pumps[pump - 1]

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