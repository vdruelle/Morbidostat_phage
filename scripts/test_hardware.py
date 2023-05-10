import smbus
from hardware_libraries import ADCPi, IOPi
from interface import Interface
import RPi.GPIO as GPIO


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


def test_ADCPi(threshold_voltage=0.05, light_pin = 20):
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


if __name__ == "__main__":
    test_I2C_connections()
    test_ADCPi()
