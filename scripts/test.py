import time

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from hardware_libraries import ADCPi
from test_bench import Interface


def test_WS_drift(total_time: float, dt: float = 1, savefile: str = "runs/WS_drift.tsv") -> None:
    """
    Measure weight sensor drift and save the data to a TSV file.

    Args:
        total_time: Total run time in seconds.
        dt: Time step in seconds.
        savefile: Path to the file where the data will be saved. Defaults to "runs/WS_drift.tsv".
    """
    adc = ADCPi(0x68, 0x69, 14)
    adc.set_pga(1)
    adc.set_bit_rate(14)

    WS_current_pin = 1
    WS_flexi_pin = 2

    times = np.arange(0, total_time, dt)
    voltages = pd.DataFrame(columns=["time", "WS current", "WS flexi"])

    print("Starting reading...")
    for ii in range(len(times)):
        voltages.loc[ii] = [
            times[ii],
            np.mean([adc.read_voltage(WS_current_pin) for jj in range(10)]),
            np.mean([adc.read_voltage(WS_flexi_pin) for jj in range(10)]),
        ]

        time.sleep(dt)
        if ii % 10 == 0:
            print(f"{times[ii]} / {total_time}s")
    print("Finished reading.")

    # Export the data as a TSV file
    voltages.to_csv(savefile, sep="\t")


def plot_WS_drift(filename: str, scaled: bool = False) -> None:
    """
    Load the generated data from a TSV file and plot it using matplotlib.

    Args:
        filename (str): Path to the TSV file containing the data.

    Returns:s
        None
    """
    data = pd.read_csv(filename, sep="\t")
    if scaled:
        data["WS current"] = data["WS current"] / max(data["WS current"])
        data["WS flexi"] = data["WS flexi"] / max(data["WS flexi"])

    plt.figure()
    plt.plot(data["time"], data["WS current"], label="WS current")
    plt.plot(data["time"], data["WS flexi"], label="WS flexi")
    plt.xlabel("Time [s]")
    plt.ylabel("Voltage (scaled) [V]")
    plt.legend()
    plt.grid()


if __name__ == "__main__":
    pass
