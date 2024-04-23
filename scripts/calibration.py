# Helper file to calibrate the hardware

import time

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import yaml
from interface import Interface
from scipy.stats import linregress

CALI_PATH = "calibrations/"


def calibrate_OD(
    interface: Interface,
    filename: str,
    nb_standards: int,
    vials: list = list(range(1, 16)),
    nb_measures: int = 50,
    lag: float = 0.02,
    voltage_threshold: float = 4.8,
) -> None:
    """Function to perform the calibration of the OD measurment. It is done by measuring some standard with
    known OD in each of the vial slots. It is suggested to use 4 standards that span the whole range of
    measurable OD.
    Once the procedure is complete, shows a plot with the results and saves a file with the fit parameters.
    In the savefile, first column is the slope, second column is the intercept of the voltage(OD) curve.

    Args:
        interface: Interface object from the interface.py file.
        filename: name of the save file.
        nb_standards: number of OD standard to calibrate on.
        vials: list of 1-indexed vials to calibrate. Defaults to list(range(1, 16)).
        nb_measure: number of voltage measures to average for each data point. Defaults to 1.
        lag: time between voltage measures in seconds. Defaults to 0.02.
        voltage_threshold: Used to estimate if there is overflow and exclude data point [V]. Defaults to 4.8.
    """
    assert nb_standards >= 2, "At least 2 OD standards are needed for the calibration."

    # ENH: Factor out measurement and fit code into separate functions
    ODs = []
    voltages = np.zeros((nb_standards, len(vials)))
    print()

    print("Preheating LEDs for measurments, please wait 2 minutes.")
    interface.switch_light(True)
    # time.sleep(120)

    # Measuring the voltage for all vial + OD standard combo
    for standard in range(nb_standards):  # iterating over all standards
        no_valid_standard = True
        while no_valid_standard:
            print()
            cur_OD = input(f"Enter OD of standard {standard+1}: ")  # TODO: more robust input handling error
            ODs.append(float(cur_OD))
            no_valid_standard = False

        for jj, vial_id in enumerate(vials):  # iterating over all vials for the current OD standard
            input("   Place OD standard in vial slot " + str(vial_id) + ", press enter when done")
            voltages[standard][jj] = interface.measure_OD_voltage(vial_id, lag, nb_measures)
            print(f"   Mean voltage measured: {voltages[standard][jj]}V")

    interface.switch_light(False)

    print("\nCalibration measurements complete. Now calculating voltage -> OD conversion.")
    ODs = np.array(ODs)
    fit_parameters = np.zeros((len(vials), 2))  # first columns are slope, second are intercepts

    # Computing the fit for all vials
    for ii, vial_id in enumerate(vials):
        good_measurements = voltages[:, ii] < voltage_threshold
        if good_measurements.sum() > 1:
            slope, intercept, _, _, _ = linregress(ODs[good_measurements], voltages[good_measurements, ii])
        else:
            print("Less than 2 good measurements, also using saturated measurements for vial" + str(vial_id))
            slope, intercept, _, _, _ = linregress(ODs, voltages[:, ii])
        # Probably want to save this info in the output file
        # Also, why not save all measurements for debugging/post-hoc analysis?
        fit_parameters[ii, 0] = slope
        fit_parameters[ii, 1] = intercept

    print(f"Calibration completed. Saving results in file {filename} and plotting results.")

    df = pd.DataFrame(fit_parameters, columns=["slope", "intercept"])
    df = df.assign(vial=vials)
    df = df[["vial", "slope", "intercept"]]
    df.to_csv(CALI_PATH + filename, sep="\t", index=False, header=True)

    # make figure showing calibration
    plt.figure()
    plt.plot(ODs, voltages, ".-")
    plt.xlabel("OD standard [a.u.]")
    plt.ylabel("Voltage [V]")
    plt.show()


def calibrate_pumps(interface: Interface, filename: str, pumps: list, dt: float = 120):
    """Function to perform the calibration of the pumps (do it with needles at the end of the tubes as it matters for
    flow speed !). It is done by weighing each of the calibration vials before and entering their weights, then running
    the pumps for dt seconds, and then weighing the vials again and entering their weights. Pumping rates are inferred
    from the difference in weights.
    Saves the pumping rate in a file with the given filename.

    Args:
        interface: Interface object from interface.py file.
        filename: name of the save file.
        pumps: list of the pumps to calibrate.
        dt: Pumping time for the calibration in seconds. Defaults to 10.
    """
    weights = np.zeros((2, len(pumps)))  # Pumps are columns, first line is weight before and second is after

    print(f"\nStarting pump calibration for pumps {pumps}.")

    print("\nLet's start by weighing the vials before the pumping.")
    for pump_idx, pump_id in enumerate(pumps):
        weight = input(f"    Weight of vial {pump_id}: ")
        weights[0, pump_idx] = weight
    print("Weight of vials before pumping has been saved.")

    print("\nPut inlet and outlet of all pumps in water.")
    input("When the setup is ready press enter. It will run all the pumps for 50s to fill the tubing.")
    tubes_filled = False
    while not tubes_filled:
        interface.run_all_pumps(50, True)
        tmp = input("Are the tubes filled ? [yes/no]")
        if tmp == "yes":
            tubes_filled = True

    input("\nNow put the outlet of the pumps inside their respective tubes. Press enter when ready.")

    print("Starting pumping.")
    interface.run_all_pumps(dt, True)
    print("Pumping done.")

    print("\nNow we measure the weights of the vials again.")
    for pump_idx, pump_id in enumerate(pumps):
        weight = input(f"    Weight of vial {pump_id}: ")
        weights[1, pump_idx] = weight
    print("Weight of vials after pumping has been saved.")

    print("Computing pumping rates.")
    # calculate pump_rate and save to file
    pump_rates = (weights[1, :] - weights[0, :]) / dt  # g.s^-1 <=> mL*s^-1

    print(f"Saving data in {filename}.")
    df = pd.DataFrame(pump_rates, columns=["rate"])
    df = df.assign(pump=pumps)
    df = df[["pump", "rate"]]
    df.to_csv(CALI_PATH + filename, sep="\t", index=False, header=True)


def calibrate_waste_pump(interface: Interface, filename: str, dt: float = 20):
    """Function to perform the calibration of the waste pump. It is done by connecting a couple of tubes
    (ideally >=3) through the pump, with inlet in water and outlet in separate 15mL Falcon tubes. Then
    the pump is run for dt seconds, and the user is asked for the volumes in the tubes. The flow rate
    is inferred from that and saved in a file with the given filename. The pump rate of this pump should
    not vary as it is pressure insensitive and its speed is defined by the hardware.

    Args:
        interface: Interface object from interface.py file.
        filename: name of the savefile.
        dt: Pumping time in seconds. Defaults to 20.
    """

    # Pre-fill
    print("\nStarting calibration for waste pump. Put inlets in water and outlets in an empty vial.")
    input("When the setup is ready press enter. It will run pump for 20s to fill the tubing.")
    interface.switch_waste_pump(True)
    time.sleep(20)
    interface.switch_waste_pump(False)

    input("Now put the outlets in seperate graduated 15mL tubes. Press enter when ready.")

    # Calibration
    interface.switch_waste_pump(True)
    time.sleep(dt)
    interface.switch_waste_pump(False)

    volumes = []
    while True:
        v = input("Volume in the vial ('stop' when all volumes added): ")
        if v == "stop":
            break
        else:
            volumes += [float(v)]

    pump_rate = np.mean(volumes) / dt  # mL*s^-1
    print(f"Computing average rate and saving it in {filename}.")
    with open(CALI_PATH + filename, "w") as file:
        file.write(str(pump_rate))


def calibrate_level_sensors(
    interface: Interface,
    filename: str,
    pump_times: int = [2, 4, 6, 8, 10, 12, 14],
    pumping_rate: float = 0.5,
    vials: list = list(range(1, 16)),
    nb_measures: int = 3,
    lag: float = 0.02,
    thresholds=[2, 8],
) -> None:
    """Function to perform the calibration of the level sensors. This has to be done after the calibration
    of the waste pump as it uses the pump to input a certain volume of liquid, and then calibrate readings
    depending on the increase in weight. The pump runs in reverse.
    CAREFULL: for now the calibration does consider whether it's a small vial or a big one, adjust pumping times
    accordingly !

    Args:
        interface: Interface class defined in the interface.py file.
        filename: name of the savefile.
        pump_times: Pumping time for calibration in seconds.
        pumping_rate: Pumping rate of the pump in mL/s^-1.
        vials: list of vial's level sensors to calibrate. Defaults to all vials.
        nb_measures: Number of measurements for each data point. Defaults to 3.
        lag: Time between the voltage measurements in seconds. Defaults to 0.02.
    """

    assert len(pump_times) > 2, "Cannot calibrate level sensors with less than 2 pumping times."

    print()
    print(f"Starting calibration for level sensors of vials {vials}.")
    input(f"Put the inlet and outlet of the waste pump in water to pre-fill the tubes, then press enter.")

    # interface.run_waste_pump(15, True, verbose=True)
    print(f"Pre-filling done.")

    capacitances = np.zeros((len(pump_times) + 1, len(vials)))
    interface.switch_waste_pump_direction(True)

    for vial_idx, vial_id in enumerate(vials):
        print()
        input(f"Put outlet of waste pump in the vial {vial_id}, remove remaining water, and then press enter.")
        tot_time = 0
        capacitances[0, vial_idx] = interface.measure_LS_capacitance(vial_id, lag, nb_measures)  # empty vial
        print(f"    Empty vial capacitance: {capacitances[0,vial_idx]}")

        for pump_time_idx, t in enumerate(pump_times):
            dt = t - tot_time
            # interface.run_waste_pump(dt, True, verbose=False)
            time.sleep(1)
            capacitances[pump_time_idx + 1, vial_idx] = interface.measure_LS_capacitance(vial_id, lag, nb_measures)
            tot_time = t
            print(f"    Measuring capacitance after {tot_time}s: {capacitances[pump_time_idx+1, vial_idx]}")

        print(f"Calibration of level sensor {vial_id} done.")
        print(f"Emptying vial {vial_id}.")
        # interface.run_waste_pump(pump_times[-1] + 1.5, False, verbose=False)

    interface.switch_waste_pump_direction(False)

    # Computing the fit for all vials
    volumes = np.array([0] + pump_times) * pumping_rate  # these are in mL
    fit_parameters = np.zeros((len(vials), 2))  # first columns are slope, second are intercepts

    for vial_idx, vial_id in enumerate(vials):
        good_measurements = (capacitances[:, vial_idx] > thresholds[0]) & (capacitances[:, vial_idx] < thresholds[1])
        if good_measurements.sum() > 1:
            slope, intercept, _, _, _ = linregress(
                volumes[good_measurements],
                capacitances[good_measurements, vial_idx],
            )
        else:
            print("Less than 2 good measurements, also using saturated measurements for vial" + str(vial_id))
            slope, intercept, _, _, _ = linregress(volumes, capacitances[:, vial_idx])
        fit_parameters[vial_idx, 0] = slope
        fit_parameters[vial_idx, 1] = intercept

    print(f"Calibration completed. Saving results in file {filename} and plotting results.")
    df = pd.DataFrame(fit_parameters, columns=["slope", "intercept"])
    df = df.assign(vial=vials)
    df = df[["vial", "slope", "intercept"]]
    df.to_csv(CALI_PATH + filename, sep="\t", index=False, header=True)

    # make figure showing calibration
    plt.figure()
    plt.plot(volumes, capacitances, ".-")
    plt.plot([0, volumes[-1]], [thresholds[0], thresholds[0]], "--", c="k")
    plt.plot([0, volumes[-1]], [thresholds[1], thresholds[1]], "--", c="k")
    plt.xlabel("Volume [mL]")
    plt.ylabel("Capacitance [pF]")
    plt.show()


def group_calibrations(cali_OD: str, cali_LS: str, cali_pumps: str, cali_waste_pump: str, output: str):
    fits_OD = pd.read_csv(CALI_PATH + cali_OD, sep="\t", header="infer")
    fits_LS = pd.read_csv(CALI_PATH + cali_LS, sep="\t", header="infer")
    rate_pumps = pd.read_csv(CALI_PATH + cali_pumps, sep="\t", header="infer")
    rate_waste_pump = pd.read_csv(CALI_PATH + cali_waste_pump, sep="\t", header="infer")

    print()
    print(f"Concatenating {cali_OD}, {cali_LS}, {cali_pumps} and {cali_waste_pump}")

    calibration_dict = {}

    cali_OD = {}
    for ii in fits_OD["vial"]:
        cali_OD[f"vial {ii}"] = {
            "slope": {"value": float(fits_OD[fits_OD["vial"] == ii]["slope"].values[0]), "units": "V.OD^-1"},
            "intercept": {"value": float(fits_OD[fits_OD["vial"] == ii]["intercept"].values[0]), "units": "V"},
        }
    calibration_dict["OD"] = cali_OD

    cali_LS = {}
    for ii in fits_LS["vial"]:
        cali_LS[f"vial {ii}"] = {
            "slope": {"value": float(fits_LS[fits_LS["vial"] == ii]["slope"].values[0]), "units": "pF.mL^-1"},
            "intercept": {"value": float(fits_LS[fits_LS["vial"] == ii]["intercept"].values[0]), "units": "pF"},
        }
    calibration_dict["LS"] = cali_LS

    cali_pumps = {}
    for ii in rate_pumps["pump"]:
        cali_pumps[f"pump {ii}"] = {
            "rate": {"value": float(rate_pumps[rate_pumps["pump"] == ii]["rate"].values[0]), "units": "mL.s^-1"}
        }
    calibration_dict["pumps"] = cali_pumps

    calibration_dict["waste_pump"] = {"rate": {"value": float(rate_waste_pump["rate"].values[0]), "units": "mL.s^-1"}}

    with open(CALI_PATH + output + ".yaml", "w") as f:
        yaml.dump(calibration_dict, f, sort_keys=False)

    print(f"Calibration saved in {output}.yaml")


if __name__ == "__main__":
    # Refactor into CLI for more flexible interaction
    # Can still run interactively if no arguments are passed
    # But allows extra arguments to be passed for specific actions
    # Like plotting only

    interface = Interface()
    vials = [1, 2, 3, 4, 6, 7, 8, 9, 11, 12, 13, 14]
    pumps = [1, 2, 3, 4, 5, 6, 9, 10, 11, 12, 13, 14]

    choice = input("What would you like to calibrate ? [OD, pumps, waste, WS, concatenate]: ")
    if choice == "OD":
        calibrate_OD(interface, "OD.tsv", nb_standards=4, vials=vials)
    elif choice == "pumps":
        calibrate_pumps(interface, "pumps.tsv", pumps)
    elif choice == "waste":
        calibrate_waste_pump(interface, "waste_pump.tsv")
    elif choice == "LS":
        calibrate_level_sensors(interface, "LS.tsv", vials=vials)
    elif choice == "concatenate":
        # This takes the time given by the RPi, which desyncs when it is turned off.
        # One can update it via the consol by typing (american format, months first): sudo date -s "06/07/2023 11:46"
        t = time.localtime()
        date_string = f"{t.tm_mon:02d}-{t.tm_mday:02d}-{t.tm_hour:02d}h-{t.tm_min:02d}min"
        group_calibrations("OD.tsv", "LS.tsv", "pumps.tsv", "waste_pump.tsv", date_string)
    else:
        print(f"{choice} is not in the available actions: [OD, pumps, waste, WS, concatenate]")
