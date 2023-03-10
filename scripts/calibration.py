# Helper file to calibrate the hardware

import time
import numpy as np
import matplotlib.pyplot as plt
from scipy.stats import linregress
from interface import Interface


def calibrate_OD(
        interface: Interface,
        filename: str,
        nb_standards: int,
        vials: list = list(range(1, 16)),
        nb_measures: int = 10,
        lag: float = 0.1,
        voltage_threshold: float = 4.8) -> np.ndarray:
    """Function to perform the calibration of the OD measurment. It is done by measuring some standard with
    known OD in each of the vial slots. It is suggested to use 4 standards that span the whole range of
    measurable OD.
    Once the procedure is complete, shows a plot with the results and saves a file with the fit parameters.

    Args:
        interface: Interface object from the interface.py file.
        filename: name of the save file.
        nb_standards: number of OD standard to calibrate on.
        vials: list of vials to calibrate. Defaults to list(range(1, 16)).
        nb_measure: number of voltage measures to average for each data point. Defaults to 10.
        lag: time between voltage measures in seconds. Defaults to 0.1.

    Returns:
        fit_parameters: the fit parameters from the fit of the OD to voltage relation.
    """
    assert nb_standards >= 2, "At least 2 OD standards are needed for the calibration."

    ODs = []
    voltages = np.zeros((nb_standards, len(vials)))

    # Measuring the voltage for all vial + OD standard combo
    for ii in range(nb_standards):  # iterating over all standards
        no_valid_standard = True
        while no_valid_standard:
            try:
                print()
                cur_OD = input(f"Enter OD of standard {ii+1}: ")
                ODs.append(float(cur_OD))
                no_valid_standard = False
            except BaseException:
                print("invalid entry")

        for jj, vial in enumerate(vials):  # iterating over all vials for the current OD standard
            input("   Place OD standard in vial slot " + str(vial) + ", press enter when done")
            interface.switch_light(True)
            voltages[ii][jj] = interface.measure_OD(vial, lag, nb_measures)  # Measuring voltage
            interface.switch_light(False)
            print(f"   Mean voltage measured: {voltages[ii][jj]}V")

    print()
    print("Calibration manipulation complete. Calculating voltage -> OD conversion.")
    ODs = np.array(ODs)
    fit_parameters = np.zeros((len(vials), 2))

    # Computing the fit for all vials
    for ii, vial in enumerate(vials):
        good_measurements = voltages[:, ii] < voltage_threshold
        if good_measurements.sum() > 1:
            slope, intercept, _, _, _ = linregress(ODs[good_measurements], voltages[good_measurements, ii])
        else:
            print("Less than 2 good measurements, also using saturated measurements for vial" + str(vial))
            slope, intercept, _, _, _ = linregress(ODs, voltages[:, ii])
        fit_parameters[ii, 0] = slope
        fit_parameters[ii, 1] = intercept

    print(f"Calibration completed. Saving results in file {filename} and plotting results.")
    np.savetxt(filename, fit_parameters)

    # make figure showing calibration
    plt.figure()
    plt.plot(ODs, voltages, '.-')
    plt.xlabel('OD standard [a.u.]')
    plt.ylabel('Voltage [V]')
    plt.show()

    return fit_parameters


if __name__ == "__main__":
    interface = Interface()
    calibrate_OD(interface, "test.txt", nb_standards=3, vials=[1, 2], nb_measures=1)
