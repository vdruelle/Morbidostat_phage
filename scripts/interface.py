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

        # self.pumps[0] is a dictionary with the GPIOplus number and pin number to the first pump
        self.pumps = []
        # self.weight_sensors[0] is a dictionary with the ADC number + pin number to first vial weight sensor
        self.weight_sensors = []
        # self.ODs[1] is a dictionary with the ADC number + pin number to first vial OD
        self.ODs = []
        # same as above but with only 1 value
        self.lights = {}
        # same as above but with only 1 value
        self.waste_pump = {}
        # list of integers for the vials (usally 1 to 15 included)
        self.vials = []

        # self.adcs[0] is the first ADC connected to the RPI
        self.adcs = []
        # self.iobuses[0] is the first ADC connected to the RPI
        self.iobuses = []

        # Setting hardware connections
        self.set_hardware_connections()

        # Loading calibration, it's a dict with the same format as the .yaml calibration file
        self.calibration = None
        self.load_calibration("03-21-15h-06min.yaml")
        self.turn_off()

    # --- Hardware setup ---

    def set_hardware_connections(self) -> None:
        """This function defines the physical connection from the different components to the pin of the RPi."""

        self.adcs = [ADCPi(0x68, 0x69, 18)]
        for adc in self.adcs:
            adc.set_pga(1)

        self.iobuses = [IOPi(0x20)]
        for iobus in self.iobuses:
            for ii in range(1, 17):
                iobus.set_pin_direction(ii, 0)

        self.vials = list(range(1, 3))
        self.lights = {"IOPi": 1, "pin": 1}
        self.waste_pump = {"IOPi": 1, "pin": 2}

        for ii in range(3, 9):
            self.pumps += [{"IOPi": 1, "pin": ii}]
        for ii in range(1, 5):
            self.ODs += [{"ADCPi": 1, "pin": ii}]
        for ii in range(5, 9):
            self.weight_sensors += [{"ADCPi": 1, "pin": ii}]

    def load_calibration(self, file) -> None:
        """Load the calibration file, process it and saves it in the Interface class.
        This needs to be performed with the same hardware connections as will be used for the run.

        Args:
            file: calibration file name including extension (ex: '03-21-15h-06min.yaml').
        """

        # Opening file as a dictionary
        with open("calibrations/" + file, "r") as stream:
            self.calibration = yaml.load(stream, Loader=yaml.loader.BaseLoader)

        # Converting values from string to floats
        for key1 in self.calibration.keys():
            for key2 in self.calibration[key1].keys():
                for key3 in self.calibration[key1][key2].keys():
                    self.calibration[key1][key2][key3]["value"] = float(
                        self.calibration[key1][key2][key3]["value"]
                    )

    # --- High level functions ---

    def measure_OD(self, vial: int, lag: float = 0.01, nb_measures: int = 10) -> float:
        """Measures the mean OD over nb_measures for the given vial. The lights need to be turned on for
        that to work.

        Args:
            vial: vial number.
            lag: delay between measures (in seconds). Defaults to 0.01.
            nb_measures: number of measures. Defaults to 1.

        Returns:
            Mean of the measured ODs.
        """

        IOPi, pin = self._OD_to_pin(vial)
        values = []
        for ii in range(nb_measures):
            time.sleep(lag)
            values += [self._voltage_to_OD(vial, self._measure_voltage(IOPi, pin))]
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

        IOPi, pin = self._WS_to_pin(vial)
        values = []
        for ii in range(nb_measures):
            time.sleep(lag)
            values += [self._voltage_to_weight(vial, self._measure_voltage(IOPi, pin))]
        return np.mean(values)

    def remove_waste(self, volume: float) -> None:
        """Runs the waste pump to remove a given volume.

        Args:
            volume: volume (in mL).
        """
        IOPi, pin = self.waste_pump["IOPi"], self.waste_pump["pin"]
        self.iobuses[IOPi - 1].write_pin(pin, 1)
        time.sleep(volume)
        self.iobuses[IOPi - 1].write_pin(pin, 0)

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

        self.iobuses[self.lights["IOPi"] - 1].write_pin(self.lights["pin"], state)

    def turn_off(self) -> None:
        """Turns everything controlled by the interface to off state."""
        for pump in range(1, len(self.pumps) + 1):
            IOPi, pin = self._pump_to_pin(pump)
            self.iobuses[IOPi - 1].write_pin(pin, 0)
        self.switch_light(False)
        self.iobuses[self.waste_pump["IOPi"] - 1].write_pin(self.waste_pump["pin"], 0)

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

        t = volume / self.calibration["pumps"][f"pump {pump}"]["rate"]["value"]
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

        IOPi, pin = self._pump_to_pin(pump)
        self.iobuses[IOPi - 1].write_pin(pin, 1)
        time.sleep(dt)
        self.iobuses[IOPi - 1].write_pin(pin, 0)

    # --- Low level functions ---

    def _pump_to_pin(self, pump: int) -> int:
        """Return the IOPi and pin number associated to the pump.

        Args:
            pump: number associated to the pump

        Returns:
            IOPi: IOPi number (first IOPi means self.iobuses[0])
            pin: physical pin on the IOPi
        """
        available_pumps = list(range(1, len(self.pumps) + 1))
        assert pump in available_pumps, f"Pump {pump} is not in the available pumps {available_pumps}"

        return self.pumps[pump - 1]["IOPi"], self.pumps[pump - 1]["pin"]

    def _WS_to_pin(self, vial_number: int) -> int:
        """Returns the ADCPi and pin number of the weight sensor associated to the vial.

        Args:
            vial_number: number associated to the vial.

        Returns:
            ADCPi: ADCPi number (first ADCPi means self.adcs[0])
            pin: physical pin on the ADCPi
        """
        assert vial_number in self.vials, f"Vial, {vial_number} is not in the available vials: {self.vials}"

        return self.weight_sensors[vial_number - 1]["ADCPi"], self.weight_sensors[vial_number - 1]["pin"]

    def _OD_to_pin(self, vial_number: int) -> int:
        """Returns the ADCPi and pin number of the OD associated to the vial.

        Args:
            vial_number: number associated to the vial.

        Returns:
            ADCPi: ADCPi number (first ADCPi means self.adcs[0])
            pin: physical pin on the ADCPi
        """
        assert vial_number in self.vials, f"Vial, {vial_number} is not in the available vials: {self.vials}"

        return self.ODs[vial_number - 1]["ADCPi"], self.ODs[vial_number - 1]["pin"]

    def _measure_voltage(self, adcpi: int, adc_pin: int) -> float:
        """Measures voltage from the given pin.

        Args:
            adcpi: which adcpi to use (from 1 to len(self.adcs) included)
            adc_pin: pin number.

        Returns:
            Voltage as measures by the ADCpi.
        """
        assert adcpi in list(
            range(1, len(self.adcs) + 1)
        ), f"ADCPi {adcpi} isn't in define ADCs: {list(range(1,len(self.adcs)+1))}"
        assert adc_pin in list(range(1, 9)), f"ADC pin {adc_pin} isn't in available pins {list(range(1,9))}"

        return self.adcs[adcpi - 1].read_voltage(adc_pin)


if __name__ == "__main__":
    tmp = Interface()
