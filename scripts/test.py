import time

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from hardware_libraries import ADCPi
from smbus import SMBus
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


def read_voltages(interface: Interface, vials: list) -> list:
    """Reads the voltage of the specified vials."""
    v = []
    for ii in vials:
        v.append(interface.measure_WS_voltage(ii))
    return v


def WS_test():
    interface = Interface()
    vials = [1, 2, 3]
    nb_iter = 10  # number of iterations
    verbose = True
    wait_time = 1
    volume_init = 0
    nb_iter_2 = 10
    flow_rate = float(interface.calibration["waste_pump"]["rate"]["value"])
    savefile = "runs/weight_tests.tsv"

    # Empty vials
    # interface.remove_waste(30, reversed=False, verbose=verbose)

    # Add starting volume
    interface.remove_waste(volume_init, reversed=True, verbose=verbose)
    interface.wait_mixing(wait_time)
    voltages = pd.DataFrame(columns=["time", "true volume", "vial 1", "vial 2", "vial 3"])
    voltages.loc[0] = [0, volume_init, *read_voltages(interface, vials)]

    t = 0
    for ii in range(nb_iter):
        print(f"Starting iteration {ii + 1} of {nb_iter}...")

        print("     Pumping in.")
        interface.switch_waste_pump_direction(True)
        interface.switch_waste_pump(True)
        for jj in range(nb_iter_2):
            interface.wait_mixing(wait_time)
            t += wait_time
            voltages.loc[len(voltages)] = [
                t,
                volume_init + (jj + 1) * flow_rate,
                *read_voltages(interface, vials),
            ]
        interface.switch_waste_pump(False)
        interface.switch_waste_pump_direction(False)

        print("     Waiting.")
        for jj in range(10):
            interface.wait_mixing(wait_time)
            t += wait_time
            voltages.loc[len(voltages)] = [
                t,
                volume_init + nb_iter_2 * flow_rate,
                *read_voltages(interface, vials),
            ]

        print("     Pumping out.")
        interface.switch_waste_pump(True)
        for jj in range(nb_iter_2):
            interface.wait_mixing(wait_time)
            t += wait_time
            voltages.loc[len(voltages)] = [
                t,
                volume_init + (nb_iter_2 - (jj + 1)) * flow_rate,
                *read_voltages(interface, vials),
            ]
        interface.switch_waste_pump(False)

        for jj in range(10):
            interface.wait_mixing(wait_time)
            t += wait_time
            voltages.loc[len(voltages)] = [
                t,
                volume_init,
                *read_voltages(interface, vials),
            ]

    voltages.to_csv(savefile, sep="\t")


def plot_WS_test(savefile="runs/weight_tests.tsv", scaled=False):
    data = pd.read_csv(savefile, sep="\t")
    if scaled:
        max_values = data[["true volume", "vial 1", "vial 2", "vial 3"]].max()
        data[["true volume", "vial 1", "vial 2", "vial 3"]] = data[
            ["true volume", "vial 1", "vial 2", "vial 3"]
        ].div(max_values)

    plt.figure()
    plt.plot(data["vial 1"], ".-", label="big vial")
    plt.plot(data["vial 2"], ".-", label="big vial")
    plt.plot(data["vial 3"], ".-", label="small vial small pad")
    plt.plot(data["true volume"], ".-", label="volume")
    plt.xlabel("Time [s]")
    plt.ylabel("Voltages [V]")
    plt.legend()
    plt.grid()
    plt.show()


def highdriver_stress_test(nb_iterations: int = 10, run_time: float = 60, wait_time: float = 240) -> None:
    def setup(bus: SMBus, addresses: list) -> None:
        """Configures the I2C bus for the highdriver.

        Args:
            bus: I2C bus number
            addresses: List of I2C addresses of the modules
        """
        for address in addresses:
            bus.write_byte_data(address, 0x00, 0x00)
            bus.write_byte_data(address, 0x01, 0x00)  # 0x01 is ON, 0x00 is OFF
            bus.write_byte_data(address, 0x02, 0x80)  # Frequency, 0X40 = 100Hz, 0x80 = 200Hz
            bus.write_byte_data(address, 0x03, 0x00)  # This is shape of the wave, 0x00 is sinusoidal
            bus.write_byte_data(address, 0x04, 0x00)
            bus.write_byte_data(address, 0x05, 0x00)
            bus.write_byte_data(address, 0x06, 0x00)
            bus.write_byte_data(address, 0x07, 0x00)
            bus.write_byte_data(address, 0x08, 0x00)
            # This is ramp up time + amplitude,0x31 is 250Vpp, 0 ramp time
            bus.write_byte_data(address, 0x09, 0x31)
            bus.write_byte_data(address, 0x0A, 0x01)  # This is update time

    def switch_state(bus: SMBus, addresses: list, state: bool) -> None:
        """Switches all the highdrivers on or off."""
        for address in addresses:
            if state:
                bus.write_byte_data(address, 0x01, 0x01)
            else:
                bus.write_byte_data(address, 0x01, 0x00)

    bus = SMBus(1)
    addresses = [0x78, 0x79, 0x7A, 0x7B]
    setup(bus, addresses)
    for ii in range(nb_iterations):
        switch_state(bus, addresses, True)
        time.sleep(run_time)
        switch_state(bus, addresses, False)
        time.sleep(wait_time)


if __name__ == "__main__":
    nb_iter = 100
    run_time = 180  # In seconds
    wait_time = 60  # in seconds
    highdriver_stress_test(nb_iterations=nb_iter, run_time=run_time, wait_time=wait_time)
