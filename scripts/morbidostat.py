# Main class used for the morbidostat experiments

import time

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from interface import Interface

RUN_DIRECTORY = "runs/"


class Morbidostat:
    def __init__(self) -> None:
        "Creates the morbidostat class"

        self.interface = Interface()

        # These need to be the same as the interface class
        self.cultures = [2]  # Bacterial culture vials
        self.phage_vials = [1]  # Experiment vials (with phages)
        self.vial_volume = 20  # In milliliters
        self.pumps = []
        self.set_pumps()

        self.experiment_start = time.time()

        columns = (
            ["time"]
            + [f"culture {ii}" for ii in range(1, len(self.cultures) + 1)]
            + [f"phage_vial {ii}" for ii in range(1, len(self.phage_vials) + 1)]
        )
        self.ODs = pd.DataFrame(columns=columns)
        self.weights = pd.DataFrame(columns=columns)

        self.OD_savefile = RUN_DIRECTORY + "ODs.tsv"
        self.weights_savefile = RUN_DIRECTORY + "weights.tsv"

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

        self.ODs.loc[len(self.ODs)] = [self.experiment_time()] + ODs

    def record_weights(self) -> None:
        """Measures weights of all vials and store these values along with the appropriate experiment time."""
        weights = []
        for vial in self.cultures + self.phage_vials:
            weights += [self.interface.measure_weight(vial)]

        self.weights.loc[len(self.ODs)] = [self.experiment_time()] + weights

    def save_data(self) -> None:
        """Saves OD and weights data to file."""
        self.ODs.to_csv(self.OD_savefile, sep="\t", index=False)
        self.weights.to_csv(self.weights_savefile, sep="\t", index=False)

    def maintain_cultures(self, target_OD: float = 0.5, verbose: bool = False) -> list:
        """Maintain all cultures at the target OD.

        Args:
            target_OD: target OD of the cultures. Defaults to 0.5.

        Returns:
            list of media volumes added to the cultures.
        """
        volumes_added = []
        for culture in range(len(self.cultures)):
            volumes_added.append(self.maintain_culture(culture, target_OD, verbose))
        self.interface.execute_pumping()
        return volumes_added

    def maintain_culture(self, culture_idx, target_OD: float = 0.5, verbose: bool = False) -> float:
        """Perform dilution of the culture to reach target OD (if above target) or does nothing (if below).

        Args:
            culture: culture number (1 is the first culture)
            target_OD: od to reach. Defaults to 0.5.
            verbose: prints information regarding the function. Defaults to False.

        Returns:
            volume added to the culture (in mL).
        """
        current_OD = self.interface.measure_OD(self.cultures[culture_idx])
        volume_to_pump = 0
        if current_OD > target_OD:
            dilution_ratio = current_OD / target_OD
            volume_to_pump = (dilution_ratio - 1) * self.vial_volume
            media_pump_number = self.get_pump_number("media", 1, "culture", culture_idx + 1)
            self.interface.inject_volume(media_pump_number, volume_to_pump, verbose=verbose)

            if verbose:
                print(f"Vial {culture_idx} has OD {round(current_OD,3)}, above target OD {target_OD}.")
                print(f"Pumping {round(volume_to_pump,3)}mL via pump {media_pump_number}.")

        else:
            if verbose:
                print(f"Vial {culture_idx} has OD {current_OD}, below target OD {target_OD}.")

        return volume_to_pump

    def inject_bacteria(self, phage_vial: int, volume: float, verbose: bool = False) -> None:
        # TODO: make search for pump better so that this does not require specifying the input culture
        pump_number = self.get_pump_number("culture", 1, "phage vial", phage_vial)
        if verbose:
            print(
                f"Injecting {round(volume,3)}mL from vial {self.cultures[0]} to vial {self.phage_vials[phage_vial-1]}"
            )
        self.interface.inject_volume(pump_number, volume, verbose=verbose)

    def feedback(self) -> None:
        pass

    def cycle(self, safety_factor=2) -> None:
        """Runs a cycle of the experiment.

        Args:
            safety_factor: This controls how much more is pumped out compared to pumped in. Defaults to 2.
        """
        self.record_ODs()
        self.record_weights()

        volumes = self.maintain_cultures(0.35, verbose=True)
        # if volumes[0] > 0:
        #     self.inject_bacteria(1, volumes[0], verbose=True)

        weight = 1000
        while weight > self.weights[-1, 0]:
            weight = self.interface.measure_weight(1)
            print(f"Current weight is {weight}, removing more")
            self.inject_bacteria(1, volumes[0] / 10, verbose=True)
            self.interface.execute_pumping()
        self.interface.wait_mixing(10)

        self.record_weights()
        self.record_ODs()
        self.interface.remove_waste(max(volumes) * safety_factor, verbose=True)
        self.record_weights()

    def run(self, cycle_time=60, tot_time=3600) -> None:
        while self.experiment_time() < tot_time:
            print()
            print(f"Experiment time: {round(self.experiment_time(),1)}s")
            self.cycle()
            time.sleep(cycle_time)

    def plots(self) -> None:
        plt.figure()
        plt.plot(self.ODtimes, self.ODs)
        plt.ylabel("OD [a.u.]")
        plt.xlabel("Time [sec]")

        plt.figure()
        plt.plot(self.weighttimes, self.weights)
        plt.ylabel("Weight [grams]")
        plt.xlabel("Time [sec]")

        plt.show()


if __name__ == "__main__":
    morb = Morbidostat()
    # morb.interface.switch_light(True)
    # time.sleep(100)
    # morb.run()
    # morb.interface.switch_light(False)
