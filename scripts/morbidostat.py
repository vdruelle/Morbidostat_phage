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
        self.cultures = [
            4,
            7,
            14,
            3,
            8,
            13,
        ]  # Bacterial cultures, first 3 are BW25113, last 3 are wbbl+ variant
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

        # Pumps from LB to BW25113 cultures
        self.pumps += [create_pump(1, "media", 1, "culture", 1)]
        self.pumps += [create_pump(2, "media", 1, "culture", 2)]
        self.pumps += [create_pump(3, "media", 1, "culture", 3)]

        # Pumps from LB to wbbl(+) variant cultures
        self.pumps += [create_pump(4, "media", 1, "culture", 4)]
        self.pumps += [create_pump(5, "media", 1, "culture", 5)]
        self.pumps += [create_pump(6, "media", 1, "culture", 6)]

        # Pumps from BW25113 to phages
        self.pumps += [create_pump(7, "culture", 1, "phage vial", 1)]
        self.pumps += [create_pump(9, "culture", 2, "phage vial", 2)]
        self.pumps += [create_pump(11, "culture", 3, "phage vial", 3)]

        # Pumps from wbbl(+) variant to phages
        self.pumps += [create_pump(8, "culture", 4, "phage vial", 1)]
        self.pumps += [create_pump(10, "culture", 5, "phage vial", 2)]
        self.pumps += [create_pump(12, "culture", 6, "phage vial", 3)]

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
            weights += [self.interface.measure_weight(vial)]

        self.weights.loc[len(self.ODs)] = [self.experiment_time()] + weights

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

    def feed_phages(
        self, volume: float, tot_time: int, WT_frac_start: float, WT_stop_progress: float, verbose=False
    ) -> None:
        "Perform bacterial mix injection."
        progress = self.experiment_time() / tot_time

        if progress > WT_stop_progress:
            if verbose:
                print(f"Progress is {round(progress*100,1)}%, injecting {volume} wbbl(+)")
            self.inject_bacteria(4, 1, volume, verbose)
            self.inject_bacteria(5, 2, volume, verbose)
            self.inject_bacteria(6, 3, volume, verbose)
        else:
            vol_WT = volume * WT_frac_start * (1 - progress / WT_stop_progress)
            vol_wbbl = volume - vol_WT
            if verbose:
                print(
                    f"Progress is {round(progress*100,1)}%, injecting {vol_WT} BW25113 and {vol_wbbl} wbbl(+)"
                )

            self.inject_bacteria(1, 1, vol_WT, verbose)
            self.inject_bacteria(2, 2, vol_WT, verbose)
            self.inject_bacteria(3, 3, vol_WT, verbose)
            self.inject_bacteria(4, 1, vol_wbbl, verbose)
            self.inject_bacteria(5, 2, vol_wbbl, verbose)
            self.inject_bacteria(6, 3, vol_wbbl, verbose)

    def cycle(self, tot_time: int, safety_factor: float = 2) -> None:
        """Runs a cycle of the experiment.

        Args:
            safety_factor: This controls how much more the waste pump removes compared to what's pumped in. Defaults to 2.
        """
        self.record_ODs()
        self.record_weights()

        volumes = self.maintain_cultures(0.5, verbose=True)
        self.interface.wait_mixing(10)

        self.record_weights()
        self.record_ODs()

        min_vol = min(volumes)
        self.feed_phages(min_vol, tot_time, 0.8, 0.8, verbose=True)
        self.interface.wait_mixing(10)
        self.record_weights()
        self.record_ODs()

        self.interface.remove_waste(max(volumes) * safety_factor, verbose=True)
        self.record_ODs()
        self.record_weights()

    def run(self, cycle_time: int = 300, tot_time: int = 8 * 3600) -> None:
        self.interface.switch_light(True)
        time.sleep(100)
        while self.experiment_time() < tot_time:
            print(f"\n--- Experiment time: {round(self.experiment_time(),1)}s ---")
            self.cycle(tot_time)
            self.save_data()
            time.sleep(cycle_time)
        print("\nExperiment is finished !")
        self.interface.switch_light(False)

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
    morb.run()
