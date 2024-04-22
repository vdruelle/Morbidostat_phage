import time

import matplotlib.pyplot as plt
import numpy as np
import RPi.GPIO as GPIO
import smbus
from hardware_libraries import ADCPi, IOPi
from interface import Interface


def test_I2C_connections():
    """Tests that the addresses defined are accessible by the raspberry pi.
    Write as output which one are available and which ones are not.
    """
    bus = smbus.SMBus(1)
    IOPis = [0x20, 0x21, 0x22, 0x23]  # each HAT has 2 chips, so that's 4 I2C addresses
    ADCPis = [0x68, 0x69, 0x6A, 0x6B]  # same thing here
    MUXs = [0x70, 0x71]
    addresses = IOPis + ADCPis + MUXs

    print("Performing I2C connections test:")
    for address in addresses:
        try:
            bus.read_byte(address)
            print(f"    I2C device found at address 0x{address:02X}")
        except (OSError, IOError):
            print(f"    I2C device at address {address:02X} not found !")

    print("Scanning complete.")
    print()


def test_ADCPi(threshold_voltage=0.05, light_pin=21):
    """Reads voltage from all the pins of all the ADCPis. Perform this test with empty vials in place.
    Write as output which pin got a voltage reading that is below threshold.
    """
    adcs = [
        ADCPi(0x68, 0x69, 14),
        ADCPi(0x6A, 0x6B, 14),
    ]

    GPIO.setwarnings(False)
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(light_pin, GPIO.OUT)
    GPIO.output(light_pin, GPIO.HIGH)

    print("Performing ADCPi read tests:")
    for adc in adcs:
        for pin in range(1, 9):
            v = adc.read_voltage(pin)
            if v > threshold_voltage:
                # print(f"    ADC {adc.get_i2c_address1():02X} {adc.get_i2c_address2():02X} {pin} OK")
                print(f"    ADC {adc.get_i2c_address1():02X} {adc.get_i2c_address2():02X} {pin} voltage is {v:0.3f}")
            else:
                print(f"    ADC {adc.get_i2c_address1():02X} {adc.get_i2c_address2():02X} {pin} voltage is {v:0.3f}")

    GPIO.output(light_pin, GPIO.LOW)
    print("Scanning complete.")
    print()


def test_LS_connections(MUXs=[0x70, 0x71], sensor_address=0x48):
    """Tests that the level sensors are accessible by the raspberry pi via the multiplexers."""

    print("Performing multiplexer connections test for level sensors:")
    bus = smbus.SMBus(1)

    # Reseting the multiplexers
    for mux in MUXs:
        bus.write_byte(mux, 0)

    for mux in MUXs:
        for channel in range(0, 8):
            if mux == 0x71 and channel == 7:  # we only have 15 sensors, not 16
                pass
            else:
                try:
                    bus.write_byte(mux, 1 << channel)
                    time.sleep(0.1)
                    bus.read_byte(sensor_address)
                    print(f"    Sensor detected on mux 0x{mux:02X} channel {channel+1}!")
                except (OSError, IOError):
                    print(f"    No sensor detected on mux 0x{mux:02X} channel {channel+1}!")

        bus.write_byte(mux, 0)  # Close the mux to avoid conflict between multiplexers

    print("Scanning complete.")


def get_capacitance(bus, AD7150_I2C_ADDRESS=0x48, averaged=False):
    """Measure the capacitance from a sensor and return its values (capacitance, capdac, raw_data)."""
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


def setup_capacitance_sensor(bus, AD7150_I2C_ADDRESS=0x48):
    """Configure the sensors for proper reading of the capacitance."""

    def write_register(addr, reg, value):
        bus.write_byte_data(addr, reg, value)
        time.sleep(0.004)  # 4ms delay for register write stability

    AD7150_REG_CH1_SETUP = 0x0B
    AD7150_REG_CONFIGURATION = 0x0F
    CH1_SETUP_VALUE = 195  # shorter average, usually pretty good
    CONFIGURATION_VALUE = 49
    write_register(AD7150_I2C_ADDRESS, AD7150_REG_CH1_SETUP, CH1_SETUP_VALUE)
    write_register(AD7150_I2C_ADDRESS, AD7150_REG_CONFIGURATION, CONFIGURATION_VALUE)


def test_LS_readings(MUXs=[0x70, 0x71], sensor_address=0x48):
    """Reads the capacitance of each sensor for 10 seconds and plots their value over time.
    Perform this test with slightly slightly filled vials and then repeat with empty vials to make sure that it works.
    """

    print("Performing level sensor readings test:")
    bus = smbus.SMBus(1)

    # Reseting the multiplexers
    for mux in MUXs:
        bus.write_byte(mux, 0)

    capacitance_data = []
    for ii in range(10):
        capacitance_data_round = []
        for mux in MUXs:
            for channel in range(0, 8):
                if mux == 0x71 and channel == 7:  # we only have 15 sensors, not 16
                    pass
                else:
                    bus.write_byte(mux, 1 << channel)
                    if ii == 0:
                        setup_capacitance_sensor(bus, sensor_address)
                    capacitance, _, _ = get_capacitance(bus, sensor_address, True)
                    capacitance_data_round.append(capacitance)

            bus.write_byte(mux, 0)  # closing this mux to let the other one do its job
            time.sleep(0.02)

        time.sleep(1)
        capacitance_data.append(capacitance_data_round)

    capacitance_data = np.array(capacitance_data)

    for ii in range(15):
        plt.plot(capacitance_data[:, ii])

    plt.legend([f"Sensor {ii+1}" for ii in range(15)], loc="upper left")
    plt.xlabel("Reading number")
    plt.ylabel("Capacitance (pF)")
    plt.show()

    print("Readings complete.")


def test_pump_sound(run_time=1, interval_time=0.5):
    """Turns pump on and off to check if they are responsive to the RPi. Perform this test while listening
    to the pump noise.

    Args:
        run_time: Run time of each pumps in seconds. Defaults to 1.
    """
    IOPis = [IOPi(0x20)]
    for iopi in IOPis:
        for ii in range(1, 17):
            iopi.set_pin_direction(ii, 0)
    time.sleep(5)

    print("Performing sequential pumping")
    for iopi in IOPis:
        for ii in range(1, 17):
            iopi.write_pin(ii, 1)
            time.sleep(run_time)
            iopi.write_pin(ii, 0)
            time.sleep(interval_time)
    print("Sequential pumping done.")
    print()


def test_array_pumping(IOPi_address, run_time=10):
    """Turns all the pumps controlled by the IOPi on for the given amount of time. Perform this test with
    tubing inlet in water to see if the pumps are working.

    Args:
        IOPi_address: address of the IOPi
        run_time: Run time of the pumps in seconds. Defaults to 10.
    """
    iopi = IOPi(IOPi_address)
    for ii in range(1, 17):
        iopi.set_pin_direction(ii, 0)

    print(f"Performing array {IOPi_address:02X} pumping for {run_time}s.")
    for ii in range(1, 17):
        iopi.write_pin(ii, 1)

    time.sleep(run_time)

    for ii in range(1, 17):
        iopi.write_pin(ii, 0)
    print("Array pumping done.")
    print()
    # iopi.write_pin(9, 1)
    # time.sleep(run_time)
    # iopi.write_pin(9, 0)


if __name__ == "__main__":
    # test_I2C_connections()
    # test_ADCPi()
    # test_LS_connections()
    test_LS_readings()
    # test_pump_sound()
    # test_array_pumping(0x20, 60)
