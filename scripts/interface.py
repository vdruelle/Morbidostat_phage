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

        self.adc = ADCPi(0x68, 0x69, 16)
        self.adc.set_pga(1)
        self.adc.set_bit_rate(18)

        self.iobus = IOPi(0x20)
        for ii in range(1: 17):  # only outputs
            self.iobus.set_pin_direction(ii, 0)

    def set_pin_layout(self) -> None:
        "Defines the pins for the pumps, lights etc..."
        self.lights = 1
        self.waste_pump = 2
        self.pumps = np.arange(3, 9)
        self.ODs = np.arange(1, 5)
        self.weight_sensors = np.arange(5, 9)

    # --- Medium level functions ---
    def _volume_to_time(self, pump:int, volume:float) -> float:
        "For now it's useless, just returns 1 second always"
        return 1.0

    def _voltage_to_OD(self, voltage: float) -> float:
        "For now this useless, just returns the raw voltage"
        return voltage

    def _voltage_to_weight(self, voltage: float) -> float:
        "For now this is useless, just returns the raw voltage"
        return voltage

    def _run_pump(self, pump: int, dt: float) -> None:
        """Run the pump for a given amount of time.

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
        return self.pumps[pump_number]

    def _WS_to_pin(self, vial_number: int) -> int:
        """Return the ADCpi pin associated to the vial weight sensor.

        Args:
            vial_number: number associated to the vial

        Returns:
            ADCpi pin associated to the weight sensor
        """
        return self.weight_sensors[vial_number]

    def _OD_to_pin(self, vial_number: int) -> int:
        """Return the ADCpi pin associated to the vial phototransistor.

        Args:
            vial_number: number associated to the vial

        Returns:
            ADCpi pin associated to the phototransistor
        """
        return self.ODs[vial_number]

    def _measure_voltage(self, adc_pin: int) -> float:
        """Measures voltage from the given pin

        Args:
            adc_pin: _description_

        Returns:
            _description_
        """
        assert (
            adc_pin in self.pumps) or (
            adc_pin in self.ODs), f"ADC pin {adc_pin} isn't in defined WS and ODs"

        return self.adc.read_voltage(adc_pin)


if __name__ == "__main__":
    tmp = Interface()
