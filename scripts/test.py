import time

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from hardware_libraries import ADCPi
from smbus import SMBus
from test_bench import Interface


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


def test_capacitive_measure(sampling_time=0.1):
    from datetime import datetime

    def write_register(addr, reg, value):
        bus.write_byte_data(addr, reg, value)
        time.sleep(0.004)  # 4ms delay for register write stability

    # Define I2C bus
    bus = SMBus(1)

    # AD7150 I2C address and register definitions
    AD7150_I2C_ADDRESS = 0x48
    AD7150_REG_CH1_SETUP = 0x0B
    AD7150_REG_CONFIGURATION = 0x0F
    # CH1_SETUP_VALUE = 203  # default smoothing on the averaged registers -> pretty long average
    CH1_SETUP_VALUE = 195  # shorter average, usually pretty good
    CONFIGURATION_VALUE = 49

    # Mux switching
    tca = 0x70
    bus.write_byte(0x71, 0)
    bus.write_byte(tca, 1 << 0)

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


def switching_speed():
    "Measures how much time it takes to change channel and do a read."
    # Whole function seems to take around 6ms, with 1ms in total for all the switching
    AD7150_I2C_ADDRESS = 0x48
    tca1 = 0x70
    tca2 = 0x71

    bus = SMBus(1)
    bus.write_byte(tca1, 0)
    bus.write_byte(tca2, 0)

    data = []

    for ii in range(100):
        bus.write_byte(tca1, 1 << 0)  # Switching seems to take around 0.5ms per switch
        tmp = get_capacitance(bus, AD7150_I2C_ADDRESS, True)[0]
        bus.write_byte(tca1, 0)
        bus.write_byte(tca2, 1 << 0)
        data.append([tmp, get_capacitance(bus, AD7150_I2C_ADDRESS, True)[0]])
        bus.write_byte(tca2, 0)

    data = np.array(data)
    print(data)


if __name__ == "__main__":
    test_capacitive_measure()
    # switching_speed()
    pass
