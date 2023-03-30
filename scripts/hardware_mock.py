from __future__ import absolute_import, division, print_function, unicode_literals

import platform
import random
import re
import time


class IOPi(object):
    """
    The MCP23017 chip is split into two 8-bit ports.  Port 0 controls pins
    1 to 8 while Port 1 controls pins 9 to 16.
    When writing to or reading from a bus or port the least significant bit
    represents the lowest numbered pin on the selected port.
    #
    """

    # Define registers values from the datasheet
    IODIRA = 0x00  # IO direction A - 1= input 0 = output
    IODIRB = 0x01  # IO direction B - 1= input 0 = output
    # Input polarity A - If a bit is set, the corresponding GPIO register bit
    # will reflect the inverted value on the pin.
    IPOLA = 0x02
    # Input polarity B - If a bit is set, the corresponding GPIO register bit
    # will reflect the inverted value on the pin.
    IPOLB = 0x03
    # The GPINTEN register controls the interrupt-on-change feature for each
    # pin on port A.
    GPINTENA = 0x04
    # The GPINTEN register controls the interrupt-on-change feature for each
    # pin on port B.
    GPINTENB = 0x05
    # Default value for port A - These bits set the compare value for pins
    # configured for interrupt-on-change.  If the associated pin level is the
    # opposite from the register bit, an interrupt occurs.
    DEFVALA = 0x06
    # Default value for port B - These bits set the compare value for pins
    # configured for interrupt-on-change.  If the associated pin level is the
    # opposite from the register bit, an interrupt occurs.
    DEFVALB = 0x07
    # Interrupt control register for port A.  If 1 interrupt triggers when the
    # pin matches the default value, if 0 the interrupt triggers on state
    # change
    INTCONA = 0x08
    # Interrupt control register for port B.  If 1 interrupt triggers when the
    # pin matches the default value, if 0 the interrupt triggers on state
    # change
    INTCONB = 0x09
    IOCON = 0x0A  # see datasheet for configuration register
    GPPUA = 0x0C  # pull-up resistors for port A
    GPPUB = 0x0D  # pull-up resistors for port B
    # The INTF register reflects the interrupt condition on the port A pins of
    # any pin that is enabled for interrupts. A set bit indicates that the
    # associated pin caused the interrupt event.
    INTFA = 0x0E
    # The INTF register reflects the interrupt condition on the port B pins of
    # any pin that is enabled for interrupts.  A set bit indicates that the
    # associated pin caused the interrupt event.
    INTFB = 0x0F
    # The INTCAP register captures the GPIO port A value at the time the
    # interrupt occurred.
    INTCAPA = 0x10
    # The INTCAP register captures the GPIO port B value at the time the
    # interrupt occurred.
    INTCAPB = 0x11
    GPIOA = 0x12  # data port A
    GPIOB = 0x13  # data port B
    OLATA = 0x14  # output latches A
    OLATB = 0x15  # output latches B

    # variables
    __ioaddress = 0x20  # I2C address
    # initial configuration
    # see IOCON page in the MCP23017 datasheet for more information.
    __conf = 0x02
    __bus = None

    def __init__(self, address, initialise=True, bus=None):
        """
        IOPi object initialisation
        :param address: i2c address for the target device, 0x20 to 0x27
        :type address: int
        :param initialise: True = direction set as inputs, pull-ups disabled,
                           ports are not inverted.
                           False = device state unaltered., defaults to True
        :type initialise: bool, optional
        :param bus: I2C bus number.  If no value is set the class will try to
                    find the i2c bus automatically using the device name
        :type bus: int, optional
        """

        if address < 0x20 or address > 0x27:
            raise ValueError("__init__ i2c address out of range: 0x20 to 0x27")
        if not isinstance(initialise, bool):
            raise ValueError("__init__ initialise must be bool: True of False")

        self.__ioaddress = address
        return

    @staticmethod
    def __checkbit(byte, bit):
        """
        Internal method for reading the value of a single bit within a byte
        :param byte: input value
        :type byte: int
        :param bit: location within value to check
        :type bit: int
        :return: value of the selected bit, 0 or 1
        :rtype: int
        """
        value = 0
        if byte & (1 << bit):
            value = 1
        return value

    @staticmethod
    def __updatebyte(byte, bit, value):
        """
        Internal method for setting the value of a single bit within a byte
        :param byte: input value
        :type byte: int
        :param bit: location to update
        :type bit: int
        :param value: new bit, 0 or 1
        :type value: int
        :return: updated value
        :rtype: int
        """

        if value == 0:
            return byte & ~(1 << bit)
        elif value == 1:
            return byte | (1 << bit)

    def __set_pin(self, pin, value, a_register, b_register):
        """
        Internal method for setting the value of a single bit
        within the device registers
        :param pin: 1 to 16
        :type pin: int
        :param value: 0 or 1
        :type value: int
        :param a_register: A register, e.g. IODIRA
        :type a_register: int
        :param b_register: B register, e.g. IODIRB
        :type b_register: int
        :raises ValueError: pin out of range: 1 to 16
        :raises ValueError: value out of range: 0 or 1
        """
        reg = None
        if pin >= 1 and pin <= 8:
            reg = a_register
            pin = pin - 1
        elif pin >= 9 and pin <= 16:
            reg = b_register
            pin = pin - 9
        else:
            raise ValueError("pin out of range: 1 to 16")

        if value < 0 or value > 1:
            raise ValueError("value out of range: 0 or 1")

        print(f"[IOPi] __set_pin: {pin} {value} {reg}")

        return

    def __get_pin(self, pin, a_register, b_register):
        """
        Internal method for getting the value of a single bit
        within the device registers
        :param pin: 1 to 16
        :type pin: int
        :param a_register: A register, e.g. IODIRA
        :type a_register: int
        :param b_register: B register, e.g. IODIRB
        :type b_register: int
        :raises ValueError: pin out of range: 1 to 16
        :return: 0 or 1
        :rtype: int
        """
        value = 0

        if pin >= 1 and pin <= 8:
            curval = self.__bus.read_byte_data(self.__ioaddress, a_register)
            value = self.__checkbit(curval, pin - 1)
        elif pin >= 9 and pin <= 16:
            curval = self.__bus.read_byte_data(self.__ioaddress, b_register)
            value = self.__checkbit(curval, pin - 9)
        else:
            raise ValueError("pin out of range: 1 to 16")

        return value

    def __set_port(self, port, value, a_register, b_register):
        """
        Internal method for setting the value of a device register
        :param port: 0 or 1
        :type port: int
        :param value: 0 to 255 (0xFF)
        :type value: int
        :param a_register: A register, e.g. IODIRA
        :type a_register: int
        :param b_register: B register, e.g. IODIRB
        :type b_register: int
        :raises ValueError: port out of range: 0 or 1
        :raises ValueError: value out of range: 0 to 255 (0xFF)
        """
        if port < 0 or port > 1:
            raise ValueError("port out of range: 0 or 1")

        if value < 0 or value > 0xFF:
            raise ValueError("value out of range: 0 to 255 (0xFF)")

        if port == 0:
            self.__bus.write_byte_data(self.__ioaddress, a_register, value)
        else:
            self.__bus.write_byte_data(self.__ioaddress, b_register, value)
        return

    def __get_port(self, port, a_register, b_register):
        """
        Internal method for getting the value of a device register
        :param port: 0 or 1
        :type port: int
        :param a_register: A register, e.g. IODIRA
        :type a_register: int
        :param b_register: B register, e.g. IODIRB
        :type b_register: int
        :raises ValueError: port out of range: 0 or 1
        :return: 0 to 255 (0xFF)
        :rtype: int
        """
        if port == 0:
            return self.__bus.read_byte_data(self.__ioaddress, a_register)
        elif port == 1:
            return self.__bus.read_byte_data(self.__ioaddress, b_register)
        else:
            raise ValueError("port out of range: 0 or 1")
        return

    def __set_bus(self, value, a_register):
        """
        Internal method for writing a 16-bit value to
        two consecutive device registers
        :param value: 0 to 65535 (0xFFFF)
        :type value: int
        :param a_register: A register, e.g. IODIRA
        :type a_register: int
        :raises ValueError: value out of range: 0 to 65535 (0xFFFF)
        """
        if value >= 0x0000 and value <= 0xFFFF:
            self.__bus.write_word_data(self.__ioaddress, a_register, value)
        else:
            raise ValueError("value out of range: 0 to 65535 (0xFFFF)")
        return

    # public methods

    def set_pin_direction(self, pin, value):
        """
        Set the IO direction for an individual pin
        :param pin: pin to update, 1 to 16
        :type pin: int
        :param value: 1 = input, 0 = output
        :type value: int
        :raises ValueError:  pin is out of range, 1 to 16
        :raises ValueError:  value is out of range, 0 or 1
        """
        self.__set_pin(pin, value, self.IODIRA, self.IODIRB)
        return

    def get_pin_direction(self, pin):
        """
        Get the IO direction for an individual pin
        :param pin: pin to read, 1 to 16
        :type pin: int
        :raises ValueError:  pin is out of range, 1 to 16
        :return: 1 = input, 0 = output
        :rtype: int
        """
        return self.__get_pin(pin, self.IODIRA, self.IODIRB)

    def set_port_direction(self, port, value):
        """
        Set the direction for an IO port
        :param port: 0 = pins 1 to 8, 1 = pins 9 to 16
        :type port: int
        :param value: 8-bit number 0 to 255 (0xFF)
                      For each bit 1 = input, 0 = output
        :type value: int
        :raises ValueError:  port is out of range, 0 or 1
        :raises ValueError:  value out of range: 0 to 255 (0xFF)
        """
        self.__set_port(port, value, self.IODIRA, self.IODIRB)
        return

    def get_port_direction(self, port):
        """
        Get the direction from an IO port
        :param port: 0 = pins 1 to 8, 1 = pins 9 to 16
        :type port: int
        :return: number between 0 and 255 (0xFF)
        :rtype: int
        :raises ValueError:  port is out of range, 0 or 1
        """
        return self.__get_port(port, self.IODIRA, self.IODIRB)

    def set_bus_direction(self, value):
        """
        Set the direction for an IO bus
        :param value: 16-bit number 0 to 65535 (0xFFFF).
                      For each bit 1 = input, 0 = output
        :type value: int
        :raises ValueError:  value is out of range, 0 to 65535 (0xFFFF)
        """
        self.__set_bus(value, self.IODIRA)
        return

    def get_bus_direction(self):
        """
        Get the direction for an IO bus
        :return: 16-bit number 0 to 65535 (0xFFFF).
                 For each bit 1 = input, 0 = output
        :rtype: int
        """
        return self.__bus.read_word_data(self.__ioaddress, self.IODIRA)

    def set_pin_pullup(self, pin, value):
        """
        Set the internal 100K pull-up resistors for an individual pin
        :param pin: pin to update, 1 to 16
        :type pin: int
        :param value: 1 = enabled, 0 = disabled
        :type value: int
        :raises ValueError:  pin is out of range, 1 to 16
        :raises ValueError:  value is out of range, 0 or 1
        """
        self.__set_pin(pin, value, self.GPPUA, self.GPPUB)
        return

    def get_pin_pullup(self, pin):
        """
        Get the internal 100K pull-up resistors for an individual pin
        :param pin: pin to read, 1 to 16
        :type pin: int
        :raises ValueError:  pin is out of range, 1 to 16
        :return: 1 = enabled, 0 = disabled
        :rtype: int
        """
        return self.__get_pin(pin, self.GPPUA, self.GPPUB)

    def set_port_pullups(self, port, value):
        """
        Set the internal 100K pull-up resistors for the selected IO port
         :param port: 0 = pins 1 to 8, 1 = pins 9 to 16
        :type port: int
        :param value: 8-bit number 0 to 255 (0xFF)
                      For each bit 1 = enabled, 0 = disabled
        :type value: int
        :raises ValueError:  port is out of range, 0 or 1
        :raises ValueError: value out of range: 0 to 255 (0xFF)
        """
        self.__set_port(port, value, self.GPPUA, self.GPPUB)
        return

    def get_port_pullups(self, port):
        """
        Get the internal pull-up status for the selected IO port
        :param port: 0 = pins 1 to 8, 1 = pins 9 to 16
        :type port: int
        :return: number between 0 and 255 (0xFF)
        :rtype: int
        :raises ValueError:  port is out of range, 0 or 1
        """
        return self.__get_port(port, self.GPPUA, self.GPPUB)

    def set_bus_pullups(self, value):
        """
        Set internal 100K pull-up resistors for an IO bus
        :param value: 16-bit number 0 to 65535 (0xFFFF).
                      For each bit 1 = enabled, 0 = disabled
        :type value: int
        :raises ValueError:  value is out of range, 0 to 65535 (0xFFFF)
        """
        self.__set_bus(value, self.GPPUA)
        return

    def get_bus_pullups(self):
        """
        Get the internal 100K pull-up resistors for an IO bus
        :return: 16-bit number 0 to 65535 (0xFFFF).
                 For each bit 1 = enabled, 0 = disabled
        :rtype: int
        """
        return self.__bus.read_word_data(self.__ioaddress, self.GPPUA)

    def write_pin(self, pin, value):
        """
        Write to an individual pin 1 - 16
        :param pin: pin to update, 1 to 16
        :type pin: int
        :param value: 1 = enabled, 0 = disabled
        :type value: int
        :raises ValueError:  pin is out of range, 1 to 16
        :raises ValueError:  value is out of range, 0 or 1
        """
        self.__set_pin(pin, value, self.GPIOA, self.GPIOB)
        return

    def write_port(self, port, value):
        """
        Write to all pins on the selected port
        :param port: 0 = pins 1 to 8, 1 = pins 9 to 16
        :type port: int
        :param value: 8-bit number 0 to 255 (0xFF)
                      For each bit 1 = logic high, 0 = logic low
        :type value: int
        :raises ValueError: port out of range: 0 or 1
        :raises ValueError: value out of range: 0 to 255 (0xFF)
        """
        self.__set_port(port, value, self.GPIOA, self.GPIOB)
        return

    def write_bus(self, value):
        """
        Write to all pins on the selected bus
        :param value: 16-bit number 0 to 65535 (0xFFFF).
                      For each bit 1 = logic high, 0 = logic low
        :type value: int
        :raises ValueError:  value is out of range, 0 to 65535 (0xFFFF)
        """
        self.__set_bus(value, self.GPIOA)
        return

    def read_pin(self, pin):
        """
        Read the value of an individual pin
        :param pin: pin to read, 1 to 16
        :type pin: [type]
        :raises ValueError: pin out of range: 1 to 16
        :raises ValueError: [description]
        :return: 0 = logic level low, 1 = logic level high
        :rtype: [type]
        """
        return self.__get_pin(pin, self.GPIOA, self.GPIOB)

    def read_port(self, port):
        """
        Read all pins on the selected port
        :param port: 0 = pins 1 to 8, port 1 = pins 9 to 16
        :type port: int
        :raises ValueError: port out of range: 0 or 1
        :return: number between 0 and 255 (0xFF)
        :rtype: int
        """
        return self.__get_port(port, self.GPIOA, self.GPIOB)

    def read_bus(self):
        """
        Read all pins on the bus
        :return: 16-bit number 0 to 65535 (0xFFFF)
        :rtype: int
        """
        return self.__bus.read_word_data(self.__ioaddress, self.GPIOA)

    def invert_pin(self, pin, value):
        """
        Invert the polarity of the selected pin
        :param pin: pin to update, 1 to 16
        :type pin: int
        :param value: 0 = same logic state of the input pin,
                      1 = inverted logic state of the input pin
        :type value: int
        :raises ValueError: pin out of range: 1 to 16
        :raises ValueError: value out of range: 0 or 1
        """
        self.__set_pin(pin, value, self.IPOLA, self.IPOLB)
        return

    def get_pin_polarity(self, pin):
        """
        Get the polarity of the selected pin
        :param pin: pin to read, 1 to 16
        :type pin: int
        :raises ValueError:  pin is out of range, 1 to 16
        :return: 0 = same logic state of the input pin,
                 1 = inverted logic state of the input pin
        :rtype: int
        """
        return self.__get_pin(pin, self.IPOLA, self.IPOLB)

    def invert_port(self, port, value):
        """
        Invert the polarity of the pins on a selected port
        :param port: 0 = pins 1 to 8, 1 = pins 9 to 16
        :type port: int
        :param value: 8-bit number 0 to 255 (0xFF).  For each bit
                      0 = same logic state of the input pin,
                      1 = inverted logic state of the input pin
        :type value: int
        :raises ValueError:  port is out of range, 0 or 1
        :raises ValueError:  value is out of range, 0 to 0xFF
        """
        self.__set_port(port, value, self.IPOLA, self.IPOLB)
        return

    def get_port_polarity(self, port):
        """
        Get the polarity for the selected IO port
        :param port: 0 = pins 1 to 8, 1 = pins 9 to 16
        :type port: int
        :return: number between 0 and 255 (0xFF)
        :rtype: int
        :raises ValueError:  port is out of range, 0 or 1
        """
        return self.__get_port(port, self.IPOLA, self.IPOLB)

    def invert_bus(self, value):
        """
        Invert the polarity of the pins on the bus
        :param value: 16-bit number 0 to 65535 (0xFFFF).  For each bit
                      0 = same logic state of the input pin,
                      1 = inverted logic state of the input pin
        :type value: int
        :raises ValueError:  value is out of range, 0 to 65535 (0xFFFF)
        """
        self.__set_bus(value, self.IPOLA)
        return

    def get_bus_polarity(self):
        """
        Get the polarity of the pins on the bus
        :return: 16-bit number 0 to 65535 (0xFFFF). For each bit
                 0 = same logic state of the input pin,
                 1 = inverted logic state of the input pin
        :rtype: int
        """
        return self.__bus.read_word_data(self.__ioaddress, self.IPOLA)

    def mirror_interrupts(self, value):
        """
        Sets whether the interrupt pins INT A and INT B are independently
        connected to each port or internally connected
        :param value: 1 = The INT pins are internally connected,
                      0 = The INT pins are not connected.
                      INT A is associated with PortA and
                      INT B is associated with PortB
        :type value: int
        :raises ValueError: value out of range: 0 or 1
        """

        if value < 0 or value > 1:
            raise ValueError("value out of range: 0 or 1")

        conf = self.__bus.read_byte_data(self.__ioaddress, self.IOCON)

        if value == 0:
            conf = self.__updatebyte(conf, 6, 0)
            self.__bus.write_byte_data(self.__ioaddress, self.IOCON, conf)
        if value == 1:
            conf = self.__updatebyte(self.__conf, 6, 1)
            self.__bus.write_byte_data(self.__ioaddress, self.IOCON, conf)
        return

    def set_interrupt_polarity(self, value):
        """
        This sets the polarity of the INT output pins
        :param value: 1 = Active-high.  0 = Active-low.
        :type value: int
        :raises ValueError: value out of range: 0 or 1
        """

        if value < 0 or value > 1:
            raise ValueError("value out of range: 0 or 1")

        conf = self.__bus.read_byte_data(self.__ioaddress, self.IOCON)

        if value == 0:
            conf = self.__updatebyte(conf, 1, 0)
            self.__bus.write_byte_data(self.__ioaddress, self.IOCON, conf)
        if value == 1:
            conf = self.__updatebyte(self.__conf, 1, 1)
            self.__bus.write_byte_data(self.__ioaddress, self.IOCON, conf)

        return

    def get_interrupt_polarity(self):
        """
        Get the polarity of the INT output pins
        :return: 1 = Active-high.  0 = Active-low.
        :rtype: int
        """
        return self.__checkbit(self.__bus.read_byte_data(self.__ioaddress, self.IOCON), 1)

    def set_interrupt_type(self, port, value):
        """
        Sets the type of interrupt for each pin on the selected port
        :param port: 0 = pins 1 to 8, 1 = pins 9 to 16
        :type port: int
        :param value: 8-bit number 0 to 255 (0xFF)
                      For each bit 1 = interrupt triggers when the pin matches
                      the default value, 0 = interrupt fires on state change
        :type value: int
        :raises ValueError:  port is out of range, 0 or 1
        :raises ValueError:  value is out of range, 0 to 0xFF
        """
        self.__set_port(port, value, self.INTCONA, self.INTCONB)
        return

    def get_interrupt_type(self, port):
        """
        Get the type of interrupt for each pin on the selected port
        :param port: 0 = pins 1 to 8, 1 = pins 9 to 16
        :type port: int
        :return: 8-bit number 0 to 255 (0xFF)
                 For each bit 1 = interrupt triggers when the pin matches
                 the default value, 0 = interrupt fires on state change
        :rtype: int
        :raises ValueError: port is out of range, 0 or 1
        """
        return self.__get_port(port, self.INTCONA, self.INTCONB)

    def set_interrupt_defaults(self, port, value):
        """
        These bits set the compare value for pins configured for
        interrupt-on-change on the selected port.
        If the associated pin level is the opposite of the register bit, an
        interrupt occurs.
        :param port: 0 = pins 1 to 8, 1 = pins 9 to 16
        :type port: int
        :param value: 8-bit number 0 to 255 (0xFF)
        :type value: int
        :raises ValueError: port is out of range, 0 or 1
        :raises ValueError: value is out of range, 0 to 0xFF
        """
        self.__set_port(port, value, self.DEFVALA, self.DEFVALB)
        return

    def get_interrupt_defaults(self, port):
        """
        Get the interrupt default value for each pin on the selected port
        :param port: 0 = pins 1 to 8, 1 = pins 9 to 16
        :type port: int
        :return: 8-bit number 0 to 255 (0xFF)
        :rtype: int
        :raises ValueError: port is out of range, 0 or 1
        """
        return self.__get_port(port, self.DEFVALA, self.DEFVALB)

    def set_interrupt_on_pin(self, pin, value):
        """
        Enable interrupts for the selected pin
        :param pin: pin to update, 1 to 16
        :type pin: int
        :param value: 1 = enabled, 0 = disabled
        :type value: int
        :raises ValueError: pin is out of range, 1 to 16
        :raises ValueError: value is out of range, 0 or 1
        """
        self.__set_pin(pin, value, self.GPINTENA, self.GPINTENB)
        return

    def get_interrupt_on_pin(self, pin):
        """
        Gets whether the interrupt is enabled for the selected pin
        :param pin: pin to read, 1 to 16
        :type pin: int
        :raises ValueError: pin is out of range, 1 to 16
        :return: 1 = enabled, 0 = disabled
        :rtype: int
        """
        return self.__get_pin(pin, self.GPINTENA, self.GPINTENB)

    def set_interrupt_on_port(self, port, value):
        """
        Enable interrupts for the pins on the selected port
        :param port: 0 = pins 1 to 8, 1 = pins 9 to 16
        :type port: int
        :param value: 8-bit number 0 to 255 (0xFF)
                      For each bit 1 = enabled, 0 = disabled
        :type value: int
        :raises ValueError: port is out of range, 0 or 1
        :raises ValueError: value is out of range, 0 to 0xFF
        """
        self.__set_port(port, value, self.GPINTENA, self.GPINTENB)
        return

    def get_interrupt_on_port(self, port):
        """
        Gets whether the interrupts are enabled for the selected port
        :param port: 0 = pins 1 to 8, 1 = pins 9 to 16
        :type port: int
        :return: number between 0 and 255 (0xFF)
                 For each bit 1 = enabled, 0 = disabled
        :rtype: int
        :raises ValueError: port is out of range, 0 or 1
        """
        return self.__get_port(port, self.GPINTENA, self.GPINTENB)

    def set_interrupt_on_bus(self, value):
        """
        Enable interrupts for the pins on the bus
        :param value: 16-bit number 0 to 65535 (0xFFFF).
                      For each bit 1 = enabled, 0 = disabled
        :type value: int
        :raises ValueError: value is out of range, 0 to 65535 (0xFFFF)
        """
        self.__set_bus(value, self.GPINTENA)
        return

    def get_interrupt_on_bus(self):
        """
        Gets whether the interrupts are enabled for the bus
        :return: 16-bit number 0 to 65535 (0xFFFF).
                 For each bit 1 = enabled, 0 = disabled
        :rtype: int
        """
        return self.__bus.read_word_data(self.__ioaddress, self.GPINTENA)

    def read_interrupt_status(self, port):
        """
        Read the interrupt status for the pins on the selected port
        interrupt trigger
        :param port: 0 = pins 1 to 8, 1 = pins 9 to 16
        :type port: int
        :raises ValueError: port out of range: 0 or 1
        :return: interrupt status for the selected port
        :rtype: int
        """
        return self.__get_port(port, self.INTFA, self.INTFB)

    def read_interrupt_capture(self, port):
        """
        Read the value from the selected port at the time of the last
        interrupt trigger
        :param port: 0 = pins 1 to 8, 1 = pins 9 to 16
        :type port: int
        :raises ValueError: port out of range: 0 or 1
        :return: port value at the time of the last interrupt trigger
        :rtype: int
        """
        return self.__get_port(port, self.INTCAPA, self.INTCAPB)

    def reset_interrupts(self):
        """
        Reset the interrupts A and B to 0
        """
        tmp = self.read_interrupt_capture(0)
        tmp = self.read_interrupt_capture(1)
        del tmp
        return


# --- ADCPi ---
class Error(Exception):
    """Base class for exceptions in this module."""

    pass


class TimeoutError(Error):
    """The operation exceeded the given deadline."""

    pass


class ADCPi(object):
    def __init__(self, address=0x68, address2=0x69, rate=18, bus=None):
        """
        Class constructor - Initialise the two ADC chips with their
        I2C addresses and bit rate.
        :param address: I2C address for channels 1 to 4, defaults to 0x68
        :type address: int, optional
        :raises ValueError: address out of range 0x68 to 0x6F
        :param address2: I2C address for channels 5 to 8, defaults to 0x69
        :type address2: int, optional
        :raises ValueError: address2 out of range 0x68 to 0x6F
        :param rate: bit rate, defaults to 18
        :type rate: int, optional
        :param bus: I2C bus number.  If no value is set the class will try to
                    find the i2c bus automatically using the device name
        :type bus: int, optional
        """
        # Get I2C bus
        print("[ADCPi] Initialising ADCPi")
        if address >= 0x68 and address <= 0x6F:
            self.__adc1_address = address
        else:
            raise ValueError("address out of range 0x68 to 0x6F")

        if address2 >= 0x68 and address2 <= 0x6F:
            self.__adc2_address = address2
        else:
            raise ValueError("address2 out of range 0x68 to 0x6F")

        self.set_bit_rate(rate)

    def read_voltage(self, channel):
        """
        Returns the voltage from the selected ADC channel
        :param channel: 1 to 8
        :type channel: int
        :raises ValueError: read_voltage: channel out of range (1 to 8 allowed)
        :return: voltage
        :rtype: float
        """
        if channel < 1 or channel > 8:
            raise ValueError("read_voltage: channel out of range (1 to 8 allowed)")

        print(f"[ADCPi] Reading voltage from channel: {channel}")
        random_voltage = random.uniform(0, 5)
        print(f"[ADCPi] Mocking random voltage: {random_voltage}")

        return random_voltage

    def set_pga(self, gain):
        """
        PGA (programmable gain amplifier) gain selection
        :param gain: 1 = 1x
                     2 = 2x
                     4 = 4x
                     8 = 8x
        :type gain: int
        :raises ValueError: set_pga: gain out of range
        """

        if gain == 1:
            # bit 0 = 0, bit 1 = 0
            pass
        elif gain == 2:
            # bit 0 = 1, bit 1 = 0
            pass
        elif gain == 4:
            # bit 0 = 0, bit 1 = 1
            pass
        elif gain == 8:
            # bit 0 = 1, bit 1 = 1
            pass
        else:
            raise ValueError("set_pga: gain out of range")

        print("[ADCPi] Setting PGA gain to: " + str(gain))

        return

    def set_bit_rate(self, rate):
        """
        Sample rate and resolution
        :param rate: 12 = 12 bit (240SPS max)
                     14 = 14 bit (60SPS max)
                     16 = 16 bit (15SPS max)
                     18 = 18 bit (3.75SPS max)
        :type rate: int
        :raises ValueError: set_bit_rate: rate out of range
        """

        if rate == 12:
            pass
        elif rate == 14:
            pass
        elif rate == 16:
            pass
        elif rate == 18:
            pass
        else:
            raise ValueError("set_bit_rate: rate out of range")

        print("[ADCPi] Setting bit rate to: " + str(rate))
        return
