class InaccessibleController(object):
    """A Controller with too strict permissions to communicate to.

    This class is used by getDriverInstanceForDevice to mark a
    controller as unusable due to permission issues. Instances of this
    class are useless for anything more than representing that a
    controller exists.

    """
    def __init__(self, driver_class, dev):
        self._driver = driver_class
        self._dev = dev
        self.name = "INACCESSIBLE"

    def __repr__(self):
        return "<INACCESSIBLE %s; vendorID: %04x; productID: %04x>"%\
            (self._driver.__name__, self._dev.getVendorID(),
             self._dev.getProductID())

class CableDriver(object):
    """Abstract class for ISC controller driver.

    When interfacing with a chip using an ISC (In System
    Configuration) protocol, an ISC Controller is required to relay
    messages from the computer (often over USB) to the chip (using the
    appropriate ISC Protocol, like JTAG).

    Subclasses of CableDriver are named after specific types of
    Controllers, and include the code necessary to use the
    Controller. An instance of one of these classes represents a
    specific controller attached to the computer.

    """

    def __init__(self, dev):
        """
        Initialize general controller driver values with defaults.

        Args:
            dev (usb1.USBDevice) - Device entry the driver will control.
        """

        self._dev = dev
        self._dev_handle = None
        self._scanchain = None
        self._jtagon = False
        self._speed = None


    def __repr__(self):
        return "<%s>"%self.__class__.__name__

    def _execute_primitives(self, commands):
        """Run a list of executable primitives on this controller, and distribute the returned data to the associated TDOPromises.

        Args:
            commands: A list of Executable Primitives to be run in order.

        """
        for p in commands:
            if self._scanchain and self._scanchain._debug:
                print("  Executing", p)#pragma: no cover
            p.execute(self)

    @property
    def _handle(self):
        if not self._dev_handle:
            self._dev_handle = self._dev.open()
        return self._dev_handle

    def close_handle(self):
        if self._dev_handle:
            self._dev_handle.close()
            self._dev_handle = None

    def jtag_enable(self):
        pass #Oerride if necessary

    def jtag_disable(self):
        pass #Oerride if necessary

    @property
    def speed(self):
        if self._speed is None:
            self._speed = self._get_speed()
        return self._speed
    @speed.setter
    def speed(self, val):
        self._speed = self._set_speed(val)
