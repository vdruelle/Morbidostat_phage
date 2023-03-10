# Helper file to calibrate the hardware

import time
import numpy as np
import matplotlib.pyplot as plt
from scipy.stats import linregress
from interface import Interface


def calibrate_OD(
        interface: Interface,
        filename: str,
        vials: list = list(range(1, 16)),
        nb_measures: int = 10,
        lag: float = 0.1) -> np.ndarray:
    """Function to perform the calibration of the OD measurment. It is done by measuring some standard with 
    known OD in each of the vial slots. It is suggested to use 4 standards that span the whole range of
    measurable OD.
    Once the procedure is complete, shows a plot with the results and saves a file with the fit parameters.

    Args:
        interface: Interface object from the interface.py file.
        filename: name of the save file. 
        vials: list of vials to calibrate. Defaults to list(range(1, 16)).
        nb_measure: number of voltage measures to average for each data point. Defaults to 10.
        lag: time between voltage measures in seconds. Defaults to 0.1.

    Returns:
        fit_parameters: the fit parameters from the fit of the OD to voltage relation.
    """
    ODs = []
    voltages = []
    no_valid_standard = True
    all_cycles_measured = False

    while all_cycles_measured == False:
        while no_valid_standard:
            s = input("Enter OD of standard [q to quit]: ")
            if s == 'q':
                print("Aborting calibration")
                all_cycles_measured = True
                break

            try:
                cur_OD = float(s)
                no_valid_standard = False
            except BaseException:
                print("invalid entry")

        if not all_cycles_measured:  # prompt user for 15 measurements while q is not pressed
            ODs.append(cur_OD)
            voltages.append(np.zeros(len(vials)))
            for vi, vial in enumerate(vials):
                OKstr = input("Place OD standard in receptible " + str(vial) +
                              ", press enter when done")

                interface.switch_light(True)
                voltages[-1][vi] = interface.measure_OD(vial, lag, nb_measures)
                interface.switch_light(False)
                print(vial, "measurement ", voltages[-1][vi])
            no_valid_standard = True

    if len(ODs) > 1:
        print("Collected " + str(len(ODs)) + " OD voltage pairs, calculating voltage -> OD  conversion")
        ODs = np.array(ODs)
        voltages = np.array(voltages).T
        fit_parameters = np.zeros((len(vials), 2))
        for vi, vial in enumerate(vials):
            good_measurements = voltages[vi, :] < 4.8
            if good_measurements.sum() > 1:
                slope, intercept, r, p, stderr = linregress(
                    ODs[good_measurements], voltages[vi, good_measurements])
            else:
                print("less than 2 good measurements, also using saturated measurements for vial" + str(vial))
                slope, intercept, r, p, stderr = linregress(ODs, voltages[vi, :])
            fit_parameters[vi, :] = [slope, intercept]
            

        # make figure showing calibration
        plt.figure()
        plt.plot(ODs, voltages.T, '.-')
        plt.xlabel('OD standard [a.u.]')
        plt.ylabel('Voltage [V]')
        plt.show()

        np.savetxt(filename, fit_parameters)

    else:
        print("need measurements for at least two OD standards")

    return fit_parameters


if __name__ == "__main__":
    interface = Interface()
    calibrate_OD(interface, "test.txt", [1,2])