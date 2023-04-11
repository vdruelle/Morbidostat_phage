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
        self.phage_vials = [2]  # Experiment vials (with phages)
        self.vial_volume = 20  # In milliliters
        self.pumps = []
        self.set_pumps()

        self.experiment_start = time.time()

        self.ODs = np.zeros(len(self.cultures) + len(self.phage_vials))
        self.ODtimes = []

    def set_pumps(self):
        def create_pump(number, input_type: str, input_number: int, output_type: str, output_number: int):
            pump = {
                "number": number,
                "input": {"type": input_type, "number": input_number},
                "output": {"type": output_type, "number": output_number},
            }
            return pump

        self.pumps += [create_pump(1, "media", 1, "culture", 1)]
        self.pumps += [create_pump(2, "culture", 1, "phage vial", 1)]
        self.pumps += [create_pump(3, "phage vial", 1, "waste", 1)]

    def get_pump_number(self, input_type: str, input_number: int, output_type: str, output_number: int):
        pump = [
            p
            for p in self.pumps
            if p["input"] == {"type": input_type, "number": input_number}
            and p["output"] == {"type": output_type, "number": output_number}
        ]
        return pump[0]["number"]

    def experiment_time(self) -> float:
        """Gives the time since the experiment start in seconds.

        Returns:
            time: time since the experiment start in seconds.
        """
        return time.time() - self.experiment_start

    def record_ODs(self) -> None:
        """Measures OD in all vials and store these values along with the appropriate experiment time."""
        ODs = []
        for vial in self.cultures + self.phage_vials:
            ODs += [self.interface.measure_OD(vial)]

        np.stack(self.ODs, ODs, axis=1)
        self.ODtimes += self.experiment_time()

    def maintain_cultures(self, target_OD: float = 0.5, verbose: bool = False) -> None:
        """Maintain all cultures at the target OD.

        Args:
            target_OD: target OD of the cultures. Defaults to 0.5.
        """
        for culture in self.cultures:
            self.maintain_culture(culture, target_OD, verbose)
        self.interface.run_pumps()

    def maintain_culture(self, culture, target_OD: float = 0.5, verbose: bool = False) -> None:
        current_OD = self.interface.measure_OD(culture)
        if current_OD > target_OD:
            dilution_ratio = current_OD / target_OD
            volume_to_pump = (dilution_ratio - 1) * self.vial_volume
            media_pump_number = self.get_pump_number("media", 1, "culture", culture)
            self.interface.inject_volume(media_pump_number, volume_to_pump)

            if verbose:
                print(f"Culture {culture} has OD {current_OD}, above target OD {target_OD}.")
                print(f"Pumping {volume_to_pump}mL via pump {media_pump_number}.")

        else:
            if verbose:
                print(f"Culture {culture} has OD {current_OD}, below target OD {target_OD}.")

    def inject_bacteria(self, phage_vial: int, volume: float, verbose: bool = False) -> None:
        # TODO: make search for pump better so that this does not require specifying the input culture
        pump_number = self.get_pump_number("culture", 1, "phage vial", phage_vial)
        if verbose:
            print(
                f"Injecting {round(volume,3)}mL from vial {self.cultures[0]} to vial {self.phage_vials[phage_vial-1]}"
            )
        self.interface.inject_volume(pump_number, volume, run=True)

    def feedback(self) -> None:
        pass

    def cycle(self) -> None:
        pass

    def run(self) -> None:
        pass


if __name__ == "__main__":
    morb = Morbidostat()
    morb.interface.switch_light(True)
