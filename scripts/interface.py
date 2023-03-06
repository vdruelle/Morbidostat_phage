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

    def set_pin_layout(self) -> None:
        "Defines the pins for the pumps, lights etc..."

        self.lights = 1
        self.waste_pump = 2
        self.pumps = np.arange(3, 17)
        self.ODs = np.arange(1, 5)
        self.weight_sensors = np.arange(5, 9)


if __name__ == "__main__":
    tmp = Interface()
