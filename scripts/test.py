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


def test_capacitive_data():
    """Test capacitive reading"""

    # Function to write a byte to a specified register
    def write_register(addr, reg, value):
        bus.write_byte_data(addr, reg, value)
        time.sleep(0.004)  # 4ms delay for register write stability

    # Define I2C bus
    bus = SMBus(1)

    # AD7150 I2C address and register definitions
    AD7150_I2C_ADDRESS = 0x48
    MULTIPLEXER_ADDRESS = 0x70
    AD7150_REG_CH1_SETUP = 0x0B
    AD7150_REG_CONFIGURATION = 0x0F
    AD7150_REG_STATUS = 0x00
    CH1_SETUP_VALUE = 203
    CONFIGURATION_VALUE = 49

    # Setup AD7150
    write_register(MULTIPLEXER_ADDRESS, AD7150_REG_CH1_SETUP, CH1_SETUP_VALUE)
    write_register(MULTIPLEXER_ADDRESS, AD7150_REG_CONFIGURATION, CONFIGURATION_VALUE)
    print("Sensor setup complete.")

    try:
        while True:
            data = bus.read_i2c_block_data(MULTIPLEXER_ADDRESS, AD7150_REG_STATUS, 24)
            print(data)
            time.sleep(0.1)
    except KeyboardInterrupt:
        print("Program stopped by user.")
        bus.close()


def test_capacitive_measure(sampling_time=0.1):
    from datetime import datetime

    def write_register(addr, reg, value):
        bus.write_byte_data(addr, reg, value)
        time.sleep(0.004)  # 4ms delay for register write stability

    def get_capacitance(bus, AD7150_I2C_ADDRESS, averaged=False):
        if averaged:
            # Registers for data averaged over time
            data1 = bus.read_byte_data(AD7150_I2C_ADDRESS, 0x05)
            data2 = bus.read_byte_data(AD7150_I2C_ADDRESS, 0x06)
        else:
            # Registers for data in real time
            data1 = bus.read_byte_data(AD7150_I2C_ADDRESS, 0x01)
            data2 = bus.read_byte_data(AD7150_I2C_ADDRESS, 0x02)

        data3 = bus.read_byte_data(AD7150_I2C_ADDRESS, 0x11)

        capdac = ((data3 - 192) / 8) * 1.625  # the 1.625 there was found to be a good value by testing
        raw_data = (((data1 * 256 + data2) - 12288) / 40944) * 4  # filtered bytes (by the chip)

        return capdac + raw_data, capdac, raw_data

    # Define I2C bus
    bus = SMBus(1)

    # AD7150 I2C address and register definitions
    AD7150_I2C_ADDRESS = 0x48
    AD7150_REG_CH1_SETUP = 0x0B
    AD7150_REG_CONFIGURATION = 0x0F
    # CH1_SETUP_VALUE = 203  # default smoothing on the averaged registers -> pretty long average
    CH1_SETUP_VALUE = 195  # shorter average, usually pretty good
    CONFIGURATION_VALUE = 49

    tca = 0x71
    bus.write_byte(tca, 1 << 7)

    # Setup AD7150
    write_register(AD7150_I2C_ADDRESS, AD7150_REG_CH1_SETUP, CH1_SETUP_VALUE)
    write_register(AD7150_I2C_ADDRESS, AD7150_REG_CONFIGURATION, CONFIGURATION_VALUE)
    print("Sensor setup complete.")

    # Import necessary libraries
    import matplotlib.animation as animation

    # Define function to update plot in animation
    capacitance_data = []
    capacitance_avg_data = []
    capdac_data = []
    raw_data = []
    time_data = []

    def update_plot(frame):
        capacitance, capdac, raw_data_val = get_capacitance(bus, AD7150_I2C_ADDRESS, False)
        capacitance_avg, tmp, tmp2 = get_capacitance(bus, AD7150_I2C_ADDRESS, True)
        capacitance_data.append(capacitance)
        capdac_data.append(capdac)
        raw_data.append(raw_data_val)
        time_data.append(datetime.now())
        capacitance_avg_data.append(capacitance_avg)

        # Clear previous plot
        plt.cla()

        # Plot updated data
        plt.plot(time_data, capacitance_data, label="Capacitance")
        plt.plot(time_data, capdac_data, label="CapDAC")
        plt.plot(time_data, raw_data, label="Raw Data")
        plt.plot(time_data, capacitance_avg_data, label="Cap Avg.")
        plt.xlabel("Time")
        plt.ylabel("Values")
        plt.legend()

    # Create animation
    ani = animation.FuncAnimation(plt.gcf(), update_plot, interval=sampling_time * 1000)

    try:
        plt.show()
    except KeyboardInterrupt:
        print("Program stopped by user.")
        plt.close()
        bus.close()


def i2c_scan(bus):
    """
    Scan for I2C devices on the bus and print out their addresses.

    Args:
        None

    Returns:
        None
    """
    addresses = []
    for device in range(128):
        try:
            bus.read_byte(device)
            address = "0x%02x" % device
            addresses += [address]
        except IOError:
            pass
    time.sleep(0.1)
    return addresses


def detect_new_I2C(bus, existing=["0x20", "0x21", "0x22", "0x23", "0x68", "0x69", "0x6a", "0x6b", "0x70", "0x71"]):
    "Scan for I2C devices and check for devices other than the existing ones"
    addresses = i2c_scan(bus)

    for address in addresses:
        if address not in existing:
            print(address)


def scan_mux_addresses(bus, tca=0x70):
    """
    Scan for capacitive sensors on the mux bus and print out their channel.
    """
    for ii in range(0, 7):
        bus.write_byte(tca, 1 << ii)  # This is how you switch channel
        if "0x48" in i2c_scan(bus):
            print(f"Channel {ii} detected")
        else:
            print(f"Channel {ii} not detected")

    # Reset the mux
    bus.write_byte(tca, 0)


def switching_speed(bus, tca):
    "Measures how much time it takes to change channel and do a read."
    # Whole function seems to take around 6ms, with 1ms in total for all the switching
    AD7150_I2C_ADDRESS = 0x48
    bus.write_byte(tca, 1 << 0)  # Switching seems to take around 0.5ms per switch
    data1 = bus.read_byte_data(AD7150_I2C_ADDRESS, 0x05)
    data2 = bus.read_byte_data(AD7150_I2C_ADDRESS, 0x06)
    data3 = bus.read_byte_data(AD7150_I2C_ADDRESS, 0x11)

    bus.write_byte(tca, 1 << 1)
    data1 = bus.read_byte_data(AD7150_I2C_ADDRESS, 0x05)
    data2 = bus.read_byte_data(AD7150_I2C_ADDRESS, 0x06)
    data3 = bus.read_byte_data(AD7150_I2C_ADDRESS, 0x11)
    bus.write_byte(tca, 0)


if __name__ == "__main__":
    test_capacitive_measure()
    # bus = SMBus(1)
    # tca = 0x70
    # scan_mux_addresses(bus)
