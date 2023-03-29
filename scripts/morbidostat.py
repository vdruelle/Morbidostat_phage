# Main class used for the morbidostat experiments

import time
import numpy as np
from interface import Interface


class Morbidostat:
    def __init__(self) -> None:
        "Creates the morbidostat class"

        self.interface = Interface()

        # These need to be the same as the interface class
        self.cultures = [1]  # Bacterial culture vials
        self.phage_vials = [2] # Experiment vials (with phages)
        self.vial_volume = 18 # In milliliters

        self.experiment_start = time.time()

        self.ODs = np.zeros((len(self.vials)))
        self.ODtimes = []

    def experiment_time(self) -> float:
        return time.time() - self.experiment_start

    def record_ODs(self) -> None:
        ODs = []
        for vial in self.cultures + self.phage_vials:
            ODs += [self.interface.measure_OD(vial)]
        
        np.stack(self.ODs, ODs, axis=1)


    def maintain_cultures(self, target_OD=0.5) -> None:
        pass

    def maintain_culture(self, culture, target_OD=0.5) -> None:
        current_OD = self.interface.measure_OD(culture)
        if current_OD > target_OD:
            dilution_ratio = current_OD / target_OD
            # TODO, need to take care of the waste pump for that.



    def inject_bacteria(self, vial, volume) -> None:
        pass

    def feedback(self) -> None:
        pass

    def cycle(self) -> None:
        pass

    def run(self) -> None,
    pass
