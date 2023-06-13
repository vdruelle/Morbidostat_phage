import time

import RPi.GPIO as GPIO
import smbus
from hardware_libraries import ADCPi, IOPi
from interface import Interface


def test_I2C_connections():
    """Tests that the addresses defined are accessible by the raspberry pi.
    Write as output which one are available and which ones are not.
    """
    bus = smbus.SMBus(1)  # Use 1 for Raspberry Pi 2 and newer, 0 for older versions
    IOPis = [0x20, 0x21, 0x22, 0x23]
    ADCPis = [0x68, 0x69, 0x6A, 0x6B, 0x6C, 0x6D, 0x6E, 0x6F]
    addresses = IOPis + ADCPis

    print("Performing I2C connections test:")
    for address in addresses:
        try:
            bus.read_byte(address)
            print(f"    I2C device found at address 0x{address:02X}")
        except (OSError, IOError):
            print(f"    I2C device at address {address:02X} not found !")

    print("Scanning complete.")
    print()


def test_ADCPi(threshold_voltage=0.05, light_pin=20):
    """Reads voltage from all the pins of all the ADCPis. Perform this test with empty vials in place.
    Write as output which pin got a voltage reading that is below threshold.
    """
    adcs = [
        ADCPi(0x68, 0x69, 14),
        ADCPi(0x6A, 0x6B, 14),
        ADCPi(0x6C, 0x6D, 14),
        ADCPi(0x6E, 0x6F, 14),
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
                print(f"    ADC {adc.get_i2c_address1():02X} {adc.get_i2c_address2():02X} {pin} OK")
            else:
                print(
                    f"    ADC {adc.get_i2c_address1():02X} {adc.get_i2c_address2():02X} {pin} voltage is {v:0.3f}"
                )

    GPIO.output(light_pin, GPIO.LOW)
    print("Scanning complete.")
    print()


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


if __name__ == "__main__":
    # test_I2C_connections()
    # test_ADCPi()
    test_pump_sound()
    # test_array_pumping(0x20, 30)
