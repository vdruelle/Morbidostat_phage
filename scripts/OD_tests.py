import time

import matplotlib.pyplot as plt
import numpy as np
from interface import Interface
from scipy.optimize import curve_fit


def read_time(interface: Interface, vial: int = 1, bitrate: int = 12) -> None:
    "Test time of a read"
    adc = interface.adcs[0]
    adc.set_bit_rate(bitrate)
    ADCPi, pin = interface._OD_to_pin(vial)
    t1 = time.time()
    interface._measure_voltage(ADCPi, pin)
    # adc.read_voltage(pin)
    t2 = time.time()
    t = t2 - t1
    print(f"One read: {t2-t1}s")

    t1 = time.time()
    interface._measure_voltage(ADCPi, pin)
    # adc.read_voltage(pin)
    t2 = time.time()
    t = t2 - t1
    print(f"One read: {t2-t1}s")

    t1 = time.time()
    for ii in range(100):
        interface._measure_voltage(ADCPi, pin)
        # adc.read_voltage(pin)
    t2 = time.time()
    t = (t2 - t1) / 100
    print(f"Average over 100 reads: {t}s")


def light_switching(interface: Interface) -> None:
    "Test if there is a latency between turning the lights on and actually reading something."
    interface = Interface()
    vial = 1
    bitrate = 12
    ADCPi, pin = interface._OD_to_pin(vial)
    adc = interface.adcs[0]
    adc.set_bit_rate(bitrate)
    times = np.arange(0, 0.1, 0.0001)
    voltages = np.zeros_like(times)

    for ii, t in enumerate(times):
        interface.switch_light(True)
        time.sleep(t)
        voltages[ii] = interface._measure_voltage(ADCPi, pin)
        interface.switch_light(False)
        time.sleep(0.01)

    plt.figure()
    plt.plot(times, voltages, ".")
    plt.grid()
    plt.xlabel("Time [seconds]")
    plt.ylabel("Voltage [V]")
    plt.show()


def OD_convergence(interface: Interface) -> None:
    "Test if OD reading has a ramp up time."
    interface = Interface()
    ADCPi, pin = interface._OD_to_pin(1)
    adc = interface.adcs[0]
    adc.set_bit_rate(18)
    # adc.set_pga(8)
    dt = 0.5
    times = np.arange(dt, 300, dt)
    voltages = np.zeros_like(times)

    interface.switch_light(True)
    for ii in range(times.shape[0]):
        time.sleep(dt)
        voltages[ii] = interface._measure_voltage(ADCPi, pin)

    interface.switch_light(False)

    def f(t, a, b, tau):
        return a * np.exp(-t / tau) + b

    popt, pcov = curve_fit(f, times, voltages)
    a, b, tau = popt

    plt.figure()
    plt.plot(times, voltages, ".", label="data")
    plt.plot(times, f(times, *popt), "-", label=f"{round(a,3)}exp(-t/{round(tau, 3)}) + {round(b, 3)}")
    plt.grid()
    plt.legend()
    plt.xlabel("Time [seconds]")
    plt.ylabel("Voltage [V]")
    plt.show()


def precision(interface: Interface) -> None:
    interface = Interface()
    adc = interface.adcs[0]
    ADCPi, pin = interface._OD_to_pin(1)
    adc.set_bit_rate(18)
    dt = 0.001
    times = np.arange(0, 10, dt)
    voltages = np.zeros_like(times)

    interface.switch_light(False)
    time.sleep(1)

    for ii in range(times.shape[0]):
        voltages[ii] = adc.read_voltage(pin)
        time.sleep(dt)

    print("18 bit")
    print(f"Mean {np.mean(voltages)}, std: {np.std(voltages)}")

    adc.set_bit_rate(16)
    voltages = np.zeros_like(times)
    for ii in range(times.shape[0]):
        voltages[ii] = adc.read_voltage(pin)
        time.sleep(dt)

    print("16 bit")
    print(f"Mean {np.mean(voltages)}, std: {np.std(voltages)}")

    adc.set_bit_rate(14)
    voltages = np.zeros_like(times)
    for ii in range(times.shape[0]):
        voltages[ii] = adc.read_voltage(pin)
        time.sleep(dt)

    print("14 bit")
    print(f"Mean {np.mean(voltages)}, std: {np.std(voltages)}")

    adc.set_bit_rate(12)
    voltages = np.zeros_like(times)
    for ii in range(times.shape[0]):
        voltages[ii] = adc.read_voltage(pin)
        time.sleep(dt)

    interface.switch_light(False)

    print("12 bit")
    print(f"Mean {np.mean(voltages)}, std: {np.std(voltages)}")


if __name__ == "__main__":
    try:
        interface = Interface()
        read_time(interface, bitrate=14)
        # light_switching(interface)
        # OD_convergence(interface)
        # precision(interface)
    finally:
        interface.turn_off()
