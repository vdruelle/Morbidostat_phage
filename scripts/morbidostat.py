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

        # Vial of the cultures, as defined in Interface class
        self.cultures = [4, 7, 14]  # Bacterial cultures, they are wbbl+ variant
        self.phage_vials = [1, 10, 11]  # Experiment vials (with phages)
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
        "Creates all the pumps used for the experiment."

        def create_pump(
            number, input_type: str, input_number: int, output_type: str, output_number: int
        ) -> dict:
            """Helper function to create the pumps, which are basically dictionnaries.

            Args:
                number: pump number
                input_type: input type (media, culture, phages)
                input_number: input number
                output_type: output type (culture, phages)
                output_number: output number

            Returns:
                dictionary that corresponds to the pump.
            """
            pump = {
                "number": number,
                "input": {"type": input_type, "number": input_number},
                "output": {"type": output_type, "number": output_number},
            }
            return pump

        # Pumps from LB to wbbl(+) cultures
        self.pumps += [create_pump(1, "media", 1, "culture", 1)]
        self.pumps += [create_pump(2, "media", 1, "culture", 2)]
        self.pumps += [create_pump(4, "media", 1, "culture", 3)]

        # Pumps from wbbl(+) variant to phages
        self.pumps += [create_pump(6, "culture", 1, "phage vial", 1)]
        self.pumps += [create_pump(7, "culture", 2, "phage vial", 2)]
        self.pumps += [create_pump(8, "culture", 3, "phage vial", 3)]

    def get_pump_number(
        self, input_type: str, input_number: int, output_type: str, output_number: int
    ) -> int:
        """Helper function to find the pump number from the input and output of that pump.

        Args:
            input_type: as defined in set_pumps
            input_number: as defined in set_pumps
            output_type: as defined in set_pumps
            output_number: as defined in set_pumps

        Returns:
            Number associated to the pump.
        """
        pump = [
            p
            for p in self.pumps
            if p["input"] == {"type": input_type, "number": input_number}
            and p["output"] == {"type": output_type, "number": output_number}
        ]

        assert (
            len(pump) == 1
        ), f"Found no / more than one pump for the input {input_type} {input_number} and output {output_type} {output_number}"

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
            weights += [self.interface.measure_WS_voltage(vial)]

        self.weights.loc[len(self.weights)] = [self.experiment_time()] + weights

    def save_data(self) -> None:
        """Saves OD and weight data to file."""
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
        for culture in range(1, len(self.cultures) + 1):
            volumes_added.append(self.maintain_culture(culture, target_OD, verbose))
        self.interface.execute_pumping()
        return volumes_added

    def maintain_culture(self, culture: int, target_OD: float = 0.5, verbose: bool = False) -> float:
        """Perform dilution of the culture to reach target OD (if above target) or does nothing (if below).

        Args:
            culture: culture number (1 is the first culture)
            target_OD: od to reach. Defaults to 0.5.
            verbose: prints information regarding the function. Defaults to False.

        Returns:
            volume added to the culture (in mL).
        """
        current_OD = self.interface.measure_OD(self.cultures[culture - 1])
        volume_to_pump = 0
        if current_OD > target_OD:
            dilution_ratio = current_OD / target_OD
            volume_to_pump = (dilution_ratio - 1) * self.vial_volume
            media_pump_number = self.get_pump_number("media", 1, "culture", culture)
            self.interface.inject_volume(media_pump_number, volume_to_pump, verbose=verbose)

            if verbose:
                print(
                    f"Vial {self.cultures[culture-1]} has OD {round(current_OD,3)}, above target OD {target_OD}."
                )
                print(f"Pumping {round(volume_to_pump,3)}mL via pump {media_pump_number}.")

        else:
            if verbose:
                print(f"Vial {self.cultures[culture-1]} has OD {current_OD}, below target OD {target_OD}.")

        return volume_to_pump

    def inject_bacteria(self, culture: int, phage_vial: int, volume: float, verbose: bool = False) -> None:
        pump_number = self.get_pump_number("culture", culture, "phage vial", phage_vial)
        if verbose:
            print(
                f"Injecting {round(volume,3)}mL from vial {self.cultures[culture-1]} to vial {self.phage_vials[phage_vial-1]}"
            )
        self.interface.inject_volume(pump_number, volume, verbose=verbose)

    def feed_phages(self, volume: list[float], safety_factor: float = 0.8, verbose: bool = False):
        """
        Feeds the phages by injecting bacteria with the given volume.

        Parameters:
            volume: A list of three floats representing the volume of bacteria to be injected for each phage.
            safety_factor: This controls how is transfered from the culture to the phage vials. Defaults to 0.8.
            verbose: Whether to print detailed information during the injection process. Defaults to False.
        """
        self.inject_bacteria(1, 1, volume[0] * safety_factor, verbose)
        self.inject_bacteria(2, 2, volume[1] * safety_factor, verbose)
        self.inject_bacteria(3, 3, volume[2] * safety_factor, verbose)
        self.interface.execute_pumping()

    def cycle(self, safety_factor: float = 2) -> None:
        """Runs a cycle of the experiment.

        Args:
            safety_factor: This controls how much more the waste pump removes compared to what's pumped in. Defaults to 2.
        """
        self.record_ODs()
        self.record_weights()

        volumes = self.maintain_cultures(0.3, verbose=True)
        self.interface.wait_mixing(10)

        self.record_weights()
        self.record_ODs()

        self.feed_phages(volumes, verbose=True)
        self.interface.wait_mixing(10)
        self.record_weights()
        self.record_ODs()

        self.interface.remove_waste(max(volumes) * safety_factor, verbose=True)
        self.interface.wait_mixing(10)
        self.record_ODs()
        self.record_weights()

    def run(self, cycle_time: int = 300, tot_time: int = 7 * 24 * 3600) -> None:
        print("Starting experiment...")
        self.interface.switch_light(True)
        time.sleep(100)
        while self.experiment_time() < tot_time:
            print(
                f"\n--- Experiment time: {round(self.experiment_time(),1)}s, Progress: {(round(self.experiment_time() / tot_time,3))*100}% ---"
            )
            self.cycle()
            self.save_data()
            time.sleep(cycle_time)
        print("\nExperiment is finished !")
        self.interface.switch_light(False)

    def cleaning_cycle(self, volume: float, safety_factor: float = 2, verbose=True):
        """Performs one cycle of cleaning. This includes pumping to cultures, pumping from cultures to phage
        vials, and then removing waste.

        Args:
            volume: volume pumped for the cycle.
            safety_factor: factor to remove more than what was pumped in. Defaults to 2.
        """
        # Adding volume to culture
        for culture in range(1, len(self.cultures) + 1):
            media_pump_number = self.get_pump_number("media", 1, "culture", culture)
            self.interface.inject_volume(media_pump_number, volume, verbose=verbose)
        self.interface.execute_pumping()
        self.interface.wait_mixing(10)

        # Taking half of that volume to phage vials
        self.feed_phages([0.75 * volume, 0.75 * volume, 0.75 * volume], verbose=verbose)
        self.interface.wait_mixing(10)

        # Removing waste
        self.interface.remove_waste(volume * safety_factor, verbose)

    def empty_cultures(self, verbose: bool = True):
        """Empty most the culture vials. They are the only ones that can be emptied since the other ones don't
        have a needle that goes to the bottom. This leaves osme liquid in so that the pumps still work.

        Args:
            verbose: Defaults to True.
        """
        print()
        print("Emptying of the cultures vials in 3 steps")
        for ii in range(3):
            self.feed_phages([5, 5, 5], verbose=verbose)
            self.interface.wait_mixing(10)
            self.interface.remove_waste(10, verbose)
        print("Done emptying the culture vials")
        print()

    def fill_cultures(self, verbose: bool = True):
        """Fill most the culture vials. This is used to replace the sterile water with LB at the beginning
        of the experiment."""
        volume = 10
        safety_factor = 2
        print()
        print("Filling of the cultures vials in 5 steps")
        for ii in range(5):
            for culture in range(1, len(self.cultures) + 1):
                media_pump_number = self.get_pump_number("media", 1, "culture", culture)
                self.interface.inject_volume(media_pump_number, volume, verbose=verbose)
            self.interface.execute_pumping()
            self.interface.wait_mixing(10)
            self.interface.remove_waste(volume * safety_factor, verbose)

    def cleaning_sequence(self, nb_cycle: int = 3, volume_cycle: float = 10, wait_time: float = 60):
        """Performs the cleaning sequence for one input (bleach, citric acid or miliQ water)

        Args:
            nb_cycle: Number of cycles to run. Defaults to 3.
            volume_cycle: Volume used per cycle per vial. Defaults to 10.
            wait_time: Waiting time between cycles (in seconds). Defaults to 60.
        """
        print()
        print(f"--- Starting cleaning sequence with {nb_cycle} time {volume_cycle}mL ---")
        print()

        for ii in range(nb_cycle):
            print(f"\nCleaning cycle {ii+1}")
            self.cleaning_cycle(volume_cycle, verbose=True)
            print(f"Waiting for {wait_time} seconds.")
            time.sleep(wait_time)

        self.empty_cultures(True)
        print()
        print("--- Finished cleaning sequence ! ---")


if __name__ == "__main__":
    morb = Morbidostat()
    # morb.run()
