# Main class used for the morbidostat experiments

import os
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
        self.cultures = [5, 10, 15]  # Bacterial cultures, they are wbbl+ variant
        self.phage_vials = [1, 2, 3, 6, 7, 8, 11, 12, 13]  # Experiment vials (with phages)
        self.culture_volume = 20  # In milliliters
        self.target_OD = 0.4
        self.pumps = []
        self.set_pumps()

        self.experiment_start = time.time()

        columns = (
            ["time"]
            + [f"culture {ii}" for ii in range(1, len(self.cultures) + 1)]
            + [f"phage_vial {ii}" for ii in range(1, len(self.phage_vials) + 1)]
        )
        self.ODs = pd.DataFrame(columns=columns)
        self.volumes = pd.DataFrame(columns=columns)

        self.OD_savefile = RUN_DIRECTORY + "ODs.tsv"
        # self.volumes_savefile = RUN_DIRECTORY + "volumes.tsv"
        self.volumes_savefile = RUN_DIRECTORY + "capacitances.tsv"

    def set_pumps(self):
        "Creates all the pumps used for the experiment."

        def create_pump(number, input_type: str, input_number: int, output_type: str, output_number: int) -> dict:
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
        self.pumps += [create_pump(3, "media", 1, "culture", 3)]

        # Pumps from wbbl(+) variant to phages
        self.pumps += [create_pump(4, "culture", 1, "phage vial", 1)]
        self.pumps += [create_pump(5, "culture", 1, "phage vial", 2)]
        self.pumps += [create_pump(6, "culture", 1, "phage vial", 3)]
        self.pumps += [create_pump(9, "culture", 2, "phage vial", 4)]
        self.pumps += [create_pump(10, "culture", 2, "phage vial", 5)]
        self.pumps += [create_pump(11, "culture", 2, "phage vial", 6)]
        self.pumps += [create_pump(13, "culture", 3, "phage vial", 7)]
        self.pumps += [create_pump(14, "culture", 3, "phage vial", 8)]
        self.pumps += [create_pump(15, "culture", 3, "phage vial", 9)]

    def get_pump_number(self, input_type: str, input_number: int, output_type: str, output_number: int) -> int:
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
        """Measures OD in all vials and store these values along with the appropriate experiment time.
        Takes around 3sec for all vials."""
        ODs = []
        for vial in self.cultures + self.phage_vials:
            ODs += [self.interface.measure_OD(vial)]

        self.ODs.loc[len(self.ODs)] = [round(time.time(), 1)] + ODs

    def record_volumes(self) -> None:
        """Measures volumes of all vials and store these values along with the appropriate experiment time.
        Takes around 3sec for all vials."""
        volumes = []
        for vial in self.cultures + self.phage_vials:
            # volumes += [self.interface.measure_volume(vial),3)]
            volumes += [round(self.interface.measure_LS_capacitance(vial), 3)]

        self.volumes.loc[len(self.volumes)] = [round(time.time(), 1)] + volumes

    def save_data(self) -> None:
        """Append the ODs and volumes to the savefiles and clear the dataframes to avoid excessive size."""
        header = not os.path.exists(self.OD_savefile)
        self.ODs.to_csv(self.OD_savefile, mode="a", header=header, index=False, sep="\t")
        self.ODs.drop(self.ODs.index, inplace=True)
        header = not os.path.exists(self.volumes_savefile)
        self.volumes.to_csv(self.volumes_savefile, mode="a", header=header, index=False, sep="\t")
        self.volumes.drop(self.volumes.index, inplace=True)

    def maintain_cultures(self, target_OD: float = 0.3, verbose: bool = False) -> list:
        """Maintain all cultures at the target OD.

        Args:
            target_OD: target OD of the cultures. Defaults to 0.3.

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
            volume_to_pump = (dilution_ratio - 1) * self.culture_volume
            media_pump_number = self.get_pump_number("media", 1, "culture", culture)
            if verbose:
                print(f"Vial {self.cultures[culture-1]} has OD {round(current_OD,3)}, above target OD {target_OD}.")
                print(f"Pumping {round(volume_to_pump,3)}mL via pump {media_pump_number}.")

            self.interface.inject_volume(media_pump_number, volume_to_pump, verbose=verbose)

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
        self.interface.inject_volume(pump_number, volume, max_volume=3, verbose=verbose)

    def feed_phages(self, volume: list[float], safety_factor: float = 0.7, verbose: bool = False):
        """
        Feeds the phages by injecting bacteria with the given volume.

        Parameters:
            volume: A list of three floats representing the volume of bacteria to be injected for each phage.
            safety_factor: This controls how is transfered from the culture to the phage vials. Defaults to 0.8.
            verbose: Whether to print detailed information during the injection process. Defaults to False.
        """
        self.inject_bacteria(1, 1, volume[0] * 0.33 * safety_factor, verbose)
        self.inject_bacteria(1, 2, volume[0] * 0.33 * safety_factor, verbose)
        self.inject_bacteria(1, 3, volume[0] * 0.33 * safety_factor, verbose)
        self.inject_bacteria(2, 4, volume[1] * 0.33 * safety_factor, verbose)
        self.inject_bacteria(2, 5, volume[1] * 0.33 * safety_factor, verbose)
        self.inject_bacteria(2, 6, volume[1] * 0.33 * safety_factor, verbose)
        self.inject_bacteria(3, 7, volume[2] * 0.33 * safety_factor, verbose)
        self.inject_bacteria(3, 8, volume[2] * 0.33 * safety_factor, verbose)
        self.inject_bacteria(3, 9, volume[2] * 0.33 * safety_factor, verbose)
        self.interface.execute_pumping()

    def cycle(self, safety_factor: float = 2) -> None:
        """Runs a cycle of the experiment.

        Args:
            safety_factor: This controls how much more the waste pump removes compared to what's pumped in. Defaults to 2.
        """
        self.record_ODs()
        self.record_volumes()

        volumes = self.maintain_cultures(self.target_OD, verbose=True)
        self.interface.wait_mixing(5)

        self.record_volumes()
        self.record_ODs()

        self.feed_phages(volumes, verbose=True)
        self.interface.wait_mixing(5)
        self.record_volumes()
        self.record_ODs()

        # the min is here to account for the max volume of vials
        self.interface.remove_waste(min(10, max(volumes)) * safety_factor, verbose=True)
        self.interface.wait_mixing(5)
        self.record_ODs()
        self.record_volumes()

    def run(self, cycle_time: int = 180, tot_time: int = 15 * 24 * 3600) -> None:
        print("Starting experiment...")
        self.interface.switch_light(True)
        time.sleep(100)

        ii = 0
        while self.experiment_time() < tot_time:
            print(
                f"\n--- Experiment time: {round(self.experiment_time(),1)}s, Progress: {(round(self.experiment_time() / tot_time,3))*100}% ---"
            )
            self.cycle()
            self.save_data()
            ii += 1
            if ii % 10 == 0:
                self.top_low_cultures(nb_cycles=10, volume=10)
            time.sleep(cycle_time)
        print("\nExperiment is finished !")
        self.interface.switch_light(False)

    def top_low_cultures(self, nb_cycles: int = 10, volume: float = 10) -> None:
        """Checks OD of cultures over the last 10 cycles and if it's not increasing add some LB to the culture.
        This is to fix an issue that when the culture vial gets too low (due to phage vials drawing too much), then the
        OD doesn't change anymore and the culture just stalls.
        """

        print("\nChecking if cultures need to be topped...")
        df_OD = pd.read_csv(self.OD_savefile, sep="\t")

        for culture in range(1, len(self.cultures) + 1):
            past_OD = df_OD[f"culture {culture}"].values[-nb_cycles * 4 :]  # 4 data points per cycle
            if max(past_OD) < self.target_OD:
                print(f"Adding {volume}mL to culture {culture}")
                media_pump_number = self.get_pump_number("media", 1, "culture", culture)
                self.interface.inject_volume(media_pump_number, volume, verbose=True)

        self.interface.execute_pumping()
        print("\nDone topping cultures.")
        print()

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
        self.record_volumes()

        # Taking some of that to the phages
        self.feed_phages(
            [min(3, 0.33 * volume) for ii in range(len(self.phage_vials))], verbose=verbose, safety_factor=1
        )
        self.interface.wait_mixing(10)
        self.record_volumes()

        # Removing waste
        self.interface.remove_waste(volume * safety_factor, verbose)
        self.record_volumes()

    def empty_cultures(self, verbose: bool = True):
        """Empty most of the culture vials. They are the only ones that can be emptied since the other ones don't
        have a needle that goes to the bottom. This leaves some liquid in so that the pumps still work.

        Args:
            verbose: Defaults to True.
        """
        print()
        print("Emptying of the cultures vials in 3 steps")
        for ii in range(3):
            self.feed_phages([3 for ii in range(3)], verbose=verbose)
            self.record_volumes()
            self.interface.wait_mixing(10)
            self.interface.remove_waste(10, verbose)
            self.record_volumes()
            print(self.volumes)
        print("Done emptying the culture vials")
        print()

    def fill_vials(self, verbose: bool = True):
        """Fill the vials. This is used to replace the sterile water with LB at the beginning of the experiment."""
        volume = 10
        safety_factor = 2
        print()
        print("Filling of vials in 5 steps")
        for ii in range(5):
            for culture in range(1, len(self.cultures) + 1):
                media_pump_number = self.get_pump_number("media", 1, "culture", culture)
                self.interface.inject_volume(media_pump_number, volume, verbose=verbose)
            self.interface.execute_pumping()
            self.interface.wait_mixing(10)
            self.feed_phages([min(1, volume / len(self.cultures)) for ii in range(len(self.cultures))], verbose=verbose)
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
            print(self.volumes)
            print(f"Waiting for {wait_time} seconds.")
            time.sleep(wait_time)
            print()

        self.empty_cultures(True)
        print()
        print("--- Finished cleaning sequence ! ---")

    def test_pump_settings(self):
        """Function to test the pumps as defined in the morbidostat class. The idea is to use each pump one at a time
        and output the volumes from the level sensors at the same time to control whether there is indeed a change of level
        in the source and target vial.
        """

        def test_media_pump(culture: int) -> None:
            pump = self.get_pump_number("media", 1, "culture", culture)
            print()
            print(f"Testing input pump {pump} for culture in vial {self.cultures[culture-1]}")
            volumes = [5, 5]

            measured_volume = self.interface.measure_LS_capacitance(self.cultures[culture - 1])
            print(f"  Capacitance in vial {self.cultures[culture - 1]}: {round(measured_volume,3)}pF")
            for vol in volumes:
                self.interface.inject_volume(pump, vol, run=True, verbose=False)
                time.sleep(1)
                measured_volume = self.interface.measure_LS_capacitance(self.cultures[culture - 1])
                print(f"  Capacitance in vial {self.cultures[culture - 1]}: {round(measured_volume,3)}pF")

        def test_phage_pump(culture: int, phage_vial: int) -> None:
            pump = self.get_pump_number("culture", culture, "phage vial", phage_vial)
            print()
            print(
                f"Testing pump {pump} from vial {self.cultures[culture-1]} to phage in vial {self.phage_vials[phage_vial-1]}."
            )
            volumes = [1, 1]

            measured_volume = self.interface.measure_LS_capacitance(self.phage_vials[phage_vial - 1])
            print(f"  Capacitance in vial {self.phage_vials[phage_vial - 1]}: {round(measured_volume,3)}pF")
            for vol in volumes:
                self.interface.inject_volume(pump, vol, run=True, verbose=False)
                time.sleep(1)
                measured_volume = self.interface.measure_LS_capacitance(self.phage_vials[phage_vial - 1])
                print(f"  Capacitance in vial {self.phage_vials[phage_vial - 1]}: {round(measured_volume,3)}pF")

        # Start with empty vials and test the pumps from media to culture
        self.interface.remove_waste(15, verbose=True)
        for culture in range(1, len(self.cultures) + 1):
            test_media_pump(culture)
        test_phage_pump(1, 1)
        test_phage_pump(1, 2)
        test_phage_pump(1, 3)
        test_phage_pump(2, 4)
        test_phage_pump(2, 5)
        test_phage_pump(2, 6)
        test_phage_pump(3, 7)
        test_phage_pump(3, 8)
        test_phage_pump(3, 9)
        self.interface.remove_waste(15, verbose=True)


if __name__ == "__main__":
    morb = Morbidostat()
    # morb.run()
