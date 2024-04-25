# Defines the class `interface` with all the hardware relations (which pin is what) and the default functions
# to run the morbidostat. The pumping the low level functions can be taken care of with the `asyncio` library to run
# them all at the same time.

import asyncio
import time

import numpy as np
import RPi.GPIO as GPIO
import smbus
import yaml

MOCK = False


if MOCK is False:
    from hardware_libraries import ADCPi, IOPi
else:
    from hardware_mock import ADCPi, IOPi


class Interface:
    def __init__(self) -> None:
        "Creates the Interface class"

        # self.pumps[0] is a dictionary with the GPIOplus number and pin number to the first pump
        self.pumps = []
        # self.ODs[0] is a dictionary with the ADC number + pin number to first vial OD
        self.ODs = []
        # self.LS[0] is a dictionary with the multiplexer address + channel number to first vial level sensor
        self.LS = []
        # This is the pin number (on the RPi, not on the IOPi) for the lights
        self.lights = None
        # This is the pin number (on the RPi, not on the IOPi) for the waste pump
        self.waste_pump = None
        # list of integers for the vials (usally 1 to 15 included)
        self.vials = []

        # self.adcs[0] is the first ADC connected to the RPI
        self.adcs = []
        # self.iobuses[0] is the first ADC connected to the RPI
        self.iobuses = []
        # asyncio tasks waiting for start
        self.asynctasks = []
        # self.muxs[0] is the address of the first multiplexer connected to the RPI
        self.muxs = []
        # I2C bus object to talk to the level sensors
        self.bus = smbus.SMBus(1)

        # Setting hardware connections
        self.set_hardware_connections()

        # Loading calibration, it's a dict with the same format as the .yaml calibration file
        self.calibration = None
        self.load_calibration("04-23-11h-22min.yaml")
        self.turn_off()

    # Destructor of the interface. Gets called when the interface object is deleted, used to reset setup.
    def __del__(self):
        print("Interface destructor called.")
        self.turn_off()
        GPIO.cleanup()

    # --- Hardware setup ---

    def set_hardware_connections(self) -> None:
        """This function defines the physical connection from the different components to the pin of the RPi."""

        # Setting up the 4 ADCPi
        self.adcs = [
            ADCPi(0x68, 0x69, 14),
            ADCPi(0x6A, 0x6B, 14),
        ]
        for adc in self.adcs:
            adc.set_pga(1)
            adc.set_bit_rate(14)  # 14 bits is read at 0.02 seconds, ~0.07mV precision with PGA 1 (8)

        # Setting up the 2 muxs addresses
        self.muxs = [0x70, 0x71]
        self.AD7150_I2C_ADDRESS = 0x48

        # Setting up the 2 IOPi (each board contains 2 chips, hence 4 addresses)
        self.iobuses = [
            IOPi(0x20),
            IOPi(0x21),
            IOPi(0x22),
            IOPi(0x23),
        ]
        # Setting all IOPi pins to write instead of read
        for iobus in self.iobuses:
            for ii in range(1, 17):
                iobus.set_pin_direction(ii, 0)

        # Setting up vials (left to right, back to front. Vial 1 is back left, vial 15 is front right)
        self.vials = list(range(1, 16))

        # Setting up lights and waste pump (controlled by the RPi directly)
        self.lights = 21  # Pin 21
        self.waste_pump = 20  # Pin 20
        self.waste_pump_direction = 16  # Pin 16, reverses the rotation of the pump when on
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(self.lights, GPIO.OUT)
        GPIO.output(self.lights, GPIO.LOW)
        GPIO.setup(self.waste_pump, GPIO.OUT)
        GPIO.output(self.waste_pump, GPIO.LOW)
        GPIO.setup(self.waste_pump_direction, GPIO.OUT)
        GPIO.output(self.waste_pump_direction, GPIO.LOW)

        # Setting up pumps
        for ii in range(1, 16):
            self.pumps += [{"IOPi": 1, "pin": ii}]

        # Setting up ODs
        for ii in range(1, 9):
            self.ODs += [{"ADCPi": 1, "pin": ii}]
        for ii in range(1, 8):
            self.ODs += [{"ADCPi": 2, "pin": ii}]

        # Setting up level sensors (harware ordering is reversed from the one of the ODs...)
        for ii in range(1, 8):
            self.LS += [{"mux": 2, "channel": 8 - ii}]
        for ii in range(1, 9):
            self.LS += [{"mux": 1, "channel": 9 - ii}]

        # Configuring capacitance sensors
        for mux in self.muxs:
            self.bus.write_byte(mux, 0)
        for mux in self.muxs:
            for channel in range(1, 9):
                if mux == 0x71 and channel == 8:  # we only have 15 sensors, not 16
                    pass
                else:
                    self.bus.write_byte(mux, 1 << channel - 1)
                    self.setup_capacitance_sensor(self.bus, self.AD7150_I2C_ADDRESS)
            self.bus.write_byte(mux, 0)

    def setup_capacitance_sensor(self, bus, sensor=0x48):
        """Configure the sensors for proper reading of the capacitance."""

        def write_register(addr, reg, value):
            bus.write_byte_data(addr, reg, value)
            time.sleep(0.004)  # 4ms delay for register write stability

        AD7150_REG_CH1_SETUP = 0x0B
        AD7150_REG_CONFIGURATION = 0x0F
        CH1_SETUP_VALUE = 195  # shorter average, usually pretty good
        CONFIGURATION_VALUE = 49
        write_register(sensor, AD7150_REG_CH1_SETUP, CH1_SETUP_VALUE)
        write_register(sensor, AD7150_REG_CONFIGURATION, CONFIGURATION_VALUE)

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
        for key1 in ["OD", "pumps", "LS"]:
            for key2 in self.calibration[key1].keys():
                for key3 in self.calibration[key1][key2].keys():
                    self.calibration[key1][key2][key3]["value"] = float(self.calibration[key1][key2][key3]["value"])

        self.calibration["waste_pump"]["rate"]["value"] = float(self.calibration["waste_pump"]["rate"]["value"])

    # --- High level functions ---

    def measure_OD(self, vial: int, lag: float = 0.02, nb_measures: int = 10) -> float:
        """Measures the mean OD over nb_measures for the given vial. The lights need to be turned on for
        that to work.

        Args:
            vial: vial number.
            lag: delay between measures (in seconds). Defaults to 0.02.
            nb_measures: number of measures. Defaults to 10.

        Returns:
            Measured OD.
        """

        return round(self._voltage_to_OD(vial, self.measure_OD_voltage(vial, lag, nb_measures)), 3)

    def measure_OD_voltage(self, vial: int, lag: float = 0.02, nb_measures: int = 10) -> float:
        """Measures voltage from phototransistor corresponding to the vial.

        Args:
            vial: vial number.
            lag: delay between measures (in seconds). Defaults to 0.02.
            nb_measures: number of measures. Defaults to 10.

        Returns:
            Mean voltage from the phototransistor.
        """
        assert lag >= 0, f"Lag value {lag} is negative."
        assert nb_measures >= 1, f"Nb of measures {nb_measures} is not suitable."

        ADCPi, pin = self._OD_to_pin(vial)
        values = []
        for ii in range(nb_measures):
            time.sleep(lag)
            values += [self._measure_voltage(ADCPi, pin)]
        return np.mean(values)

    def inject_volume(
        self, pump: int, volume: float, max_volume: float = 10, run: bool = False, verbose: bool = False
    ) -> None:
        """Queue the inject of the pump for the given volume in mL.

        Args:
            pump: pump number
            volume: volume (in mL)
            run: Whether to queue the pumping (asynchronous) or to run it directly (sequential). Defaults to False.
            verbose: whether to print actions or not. Defaults to False.
        """
        assert volume >= 0, f"Cannot inject volume {volume}."

        if volume > max_volume:
            print(
                f"""Volume to inject {round(volume,2)}mL is superior to max volume allowed at once {max_volume}. 
                  Injecting {max_volume} instead."""
            )
        dt = self._volume_to_time(pump, min(volume, max_volume))
        self.run_pump(pump, dt, run, verbose)

    def run_pump(self, pump: int, dt: float, run: bool = True, verbose: bool = True) -> None:
        """Queue the run of the pump for the given amount of time dt (in seconds).

        Args:
            pump: pump number
            dt: time (in seconds)
            run: Whether to queue the pumping (asynchronous) or to run it directly (sequential). Defaults to True.
        """
        assert dt >= 0, f"Cannot run pump for amount of time {dt}."

        if dt > 0:
            self._add_pumping(pump, dt, verbose)
            if run == True:
                self.execute_pumping()

    def run_all_pumps(self, dt: float, run: bool = True) -> None:
        """Runs all the pumps at once for the given amount of time.

        Args:
            dt: time (in seconds) of pumping.
            run:Whether to queue the pumping (asynchronous) or to run it directly (sequential). Defaults to True.
        """
        for pump in range(1, len(self.pumps) + 1):
            self.run_pump(pump, dt, False)
        if run:
            self.execute_pumping()

    def execute_pumping(self) -> None:
        """Executes all the tasks in the asynchronous tasks list and wait for them to finish."""
        loop = asyncio.get_event_loop()
        loop.run_until_complete(asyncio.gather(*self.asynctasks))
        self.asynctasks = []

    def measure_volume(self, vial: int, lag: float = 0.02, nb_measures: int = 10) -> float:
        """Measures the mean volume (in mL) over nb_measures from given vial.

        Args:
            vial: vial number.
            lag: delay between measures (in second). Defaults to 0.02.
            nb_measures: number of measures. Defaults to 10.

        Returns:
            Measured volume.
        """

        return round(self._capacitance_to_volume(vial, self.measure_LS_capacitance(vial, lag, nb_measures)), 3)

    def measure_LS_capacitance(self, vial: int, lag: float = 0.02, nb_measures: int = 10) -> float:
        """Measures the capacitance from the level sensor corresponding to the vial over nb_measure.

        Args:
            vial: vial number
            lag: delay between measures (in seconds). Defaults to 0.02.
            nb_measures: number of measures. Defaults to 1.

        Returns:
            Mean capacitance from the level sensor.
        """
        assert lag >= 0, f"Lag value {lag} is negative."
        assert nb_measures >= 1, f"Nb of measures {nb_measures} is not suitable."

        for mux in self.muxs:  # TODO handle things better so that we don't have to reset all muxes every measure
            self.bus.write_byte(mux, 0)

        mux, channel = self._LS_to_mux(vial)
        self.bus.write_byte(self.muxs[mux - 1], 1 << channel - 1)

        values = []
        for ii in range(nb_measures):
            time.sleep(lag)
            values += [self._read_capacitance()]
        return np.mean(values)

    def remove_waste(self, volume: float, verbose=False) -> None:
        """Runs the waste pump to remove a given volume.

        Args:
            volume: volume (in mL).
            verbose: whether to print actions or not. Defaults to False.
        """
        assert volume >= 0, f"Cannot remove volume {volume}."

        if verbose:
            print(f"Removing {round(volume,1)}mL via waste pump.")

        dt = volume / self.calibration["waste_pump"]["rate"]["value"]
        self.run_waste_pump(dt, False, verbose=verbose)

    def run_waste_pump(self, dt, reversed: bool = False, verbose=True) -> None:
        """Runs the waste pump for the given amount of time.

        Args:
            dt: time to run, in seconds.
            reversed: whether to run the pump in reverse or not. Defaults to False.
            verbose: Verbosity. Defaults to True.
        """
        assert dt >= 0, f"Cannot run waste pump for time {dt}."

        if verbose and not reversed:
            print(f"Running waste pump for {dt} seconds.")
        elif verbose and reversed:
            print(f"Running waste pump in reverse for {dt} seconds.")

        if dt > 0:
            self.switch_waste_pump_direction(reversed)
            self.switch_waste_pump(True)
            time.sleep(dt)
            self.switch_waste_pump(False)
            self.switch_waste_pump_direction(False)

        if verbose:
            print(f"Finished running waste pump.")

    def wait_mixing(self, dt: float, verbose=False):
        """Wait mixing for a given amount of time.

        Args:
            dt: time (in seconds).
        """
        assert dt >= 0, f"Cannot wait for time {dt}."

        if verbose:
            print(f"Waiting {dt}s for mixing.")
        if dt > 0:
            time.sleep(dt)

    def switch_light(self, state: bool) -> None:
        """Turns lights to the given state. True is on, False is off.

        Args:
            state: True turns lights on, False turns light off.
        """
        assert state in [True, False], f"State {state} is not valid"

        if state:
            GPIO.output(self.lights, GPIO.HIGH)
        else:
            GPIO.output(self.lights, GPIO.LOW)

    def switch_waste_pump(self, state: bool) -> None:
        """Turns the waste pump to the given state. True is on, False is off.

        Args:
            state: True turns the pump on, False turns the pump off.
        """
        assert state in [True, False], f"State {state} is not valid"

        if state:
            GPIO.output(self.waste_pump, GPIO.HIGH)
        else:
            GPIO.output(self.waste_pump, GPIO.LOW)

    def switch_waste_pump_direction(self, state: bool) -> None:
        """Turns the direction of the waste pump to the given state. False is default rotation.

        Args:
            state: False is default rotation, True is the reversed rotation.
        """
        assert state in [True, False], f"State {state} is not valid"

        if state:
            GPIO.output(self.waste_pump_direction, GPIO.HIGH)
        else:
            GPIO.output(self.waste_pump_direction, GPIO.LOW)

    def turn_off(self) -> None:
        """Turns everything controlled by the interface to off state."""
        for pump in range(1, len(self.pumps) + 1):
            IOPi, pin = self._pump_to_pin(pump)
            self.iobuses[IOPi - 1].write_pin(pin, 0)
        self.switch_light(False)
        self.switch_waste_pump(False)
        self.switch_waste_pump_direction(False)

    # --- Medium level functions ---

    def _volume_to_time(self, pump: int, volume: float) -> float:
        """Uses the calibration of the pump to convert a volume in mL to a pumping duration in seconds.

        Args:
            pump: pump number.
            volume: volume to pump in mL.

        Returns:
            t: time (in seconds) to pump the given volume.
        """
        assert volume >= 0, f"Volume {volume} is not valid."
        assert pump in self._available_pumps(), f"Pump {pump} is not in the available pumps {self.available_pumps()}"

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

        if voltage <= 0:
            print(f"Got OD voltage {voltage}, which is negative.")

        slope = self.calibration["OD"][f"vial {vial}"]["slope"]["value"]
        intercept = self.calibration["OD"][f"vial {vial}"]["intercept"]["value"]
        OD = (voltage - intercept) / slope

        return OD

    def _capacitance_to_volume(self, vial: int, capacitance: float) -> float:
        """Uses the calibration to convert the capacitance measure to a volume.

        Args:
            vial: vial number.
            capacitance: measured capacitance in pF.

        Returns:
            volume: volume in mL corresponding to the capacitance measured for the given vial.
        """
        assert vial in self.vials, f"Vial {vial} is not in the available vials: {self.vials}"

        if capacitance <= 0:
            print(f"Got LS capacitance {capacitance}, which is negative.")

        slope = self.calibration["LS"][f"vial {vial}"]["slope"]["value"]
        intercept = self.calibration["LS"][f"vial {vial}"]["intercept"]["value"]
        volume = (capacitance - intercept) / slope

        return volume

    def _add_pumping(self, pump: int, dt: float, verbose: bool = False) -> None:
        """Add a pumping task to the async tasks list. Used for all pumps except waste pump.
        One must call execute_pumping() to execute these tasks.

        Args:
            pump: pump number.
            dt: duration in seconds.
        """

        async def _pump_coroutine(self, pump: int, dt: float, verbose: bool) -> None:
            IOPi, pin = self._pump_to_pin(pump)
            self.iobuses[IOPi - 1].write_pin(pin, 1)
            if verbose:
                print(f"Pump {pump} start pumping.")
            await asyncio.sleep(dt)
            self.iobuses[IOPi - 1].write_pin(pin, 0)
            if verbose:
                print(f"Pump {pump} finished after {round(dt,2)} seconds.")

        assert dt > 0, f"Cannot pump for a negative amount of time {dt}"
        self.asynctasks.append(asyncio.ensure_future(_pump_coroutine(self, pump, dt, verbose)))

    # --- Low level functions ---

    def _pump_to_pin(self, pump: int) -> int:
        """Return the IOPi and pin number associated to the pump.

                Args:
                    pump: number associated to the pump
        read_voltage(adc_pin)

                Returns:
                    IOPi: IOPi number (first IOPi means self.iobuses[0])
                    pin: physical pin on the IOPi
        """
        assert pump in self._available_pumps(), f"Pump {pump} is not in the available pumps {self.available_pumps()}"

        return self.pumps[pump - 1]["IOPi"], self.pumps[pump - 1]["pin"]

    def _LS_to_mux(self, vial_number: int) -> tuple[int, int]:
        """Returns the mux address and channel number of the level sensor associated to the vial.

        Args:
            vial_number: number associated to the vial.

        Returns:
            mux: multiplexer address
            channel: multiplexer channel associated to the level sensor
        """
        assert vial_number in self.vials, f"Vial, {vial_number} is not in the available vials: {self.vials}"

        return (self.LS[vial_number - 1]["mux"], self.LS[vial_number - 1]["channel"])

    def _read_capacitance(self, averaged=True):
        """Measure the capacitance from a sensor and return its values (capacitance, capdac, raw_data)."""
        if averaged:
            # Registers for data averaged over time
            data1 = self.bus.read_byte_data(self.AD7150_I2C_ADDRESS, 0x05)
            data2 = self.bus.read_byte_data(self.AD7150_I2C_ADDRESS, 0x06)
        else:
            # Registers for data in real time
            data1 = self.bus.read_byte_data(self.AD7150_I2C_ADDRESS, 0x01)
            data2 = self.bus.read_byte_data(self.AD7150_I2C_ADDRESS, 0x02)

        data3 = self.bus.read_byte_data(self.AD7150_I2C_ADDRESS, 0x11)

        return ((data3 - 192) / 8) * 1.625 + (((data1 * 256 + data2) - 12288) / 40944) * 4

    def _OD_to_pin(self, vial_number: int) -> int:
        """Returns the ADCPi and pin number of the OD associated to the vial.

        Args:
            vial_number: number associated to the vial.

        Returns:
            ADCPi: ADCPi number (first ADCPi means self.adcs[0])
            pin: physical pin on the ADCPi
        """
        assert vial_number in self.vials, f"Vial, {vial_number} is not in the available vials: {self.vials}"

        return (self.ODs[vial_number - 1]["ADCPi"], self.ODs[vial_number - 1]["pin"])

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

    def _available_pumps(self) -> list[int]:
        "Returns the list of available pumps"
        return list(range(1, len(self.pumps) + 1))


if __name__ == "__main__":
    tmp = Interface()
