class InaccessibleController(object):
    def __init__(self, driver_class, dev):
        self._driver = driver_class
        self._dev = dev
        self.name = "INACCESSIBLE"

    def __repr__(self):
        return "<INACCESSIBLE %s; vendorID: %04x; productID: %04x>"%\
            (self._driver.__name__, self._dev.getVendorID(),
             self._dev.getProductID())

class CableDriver(object):
    """Abstract class for controller driver."""

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


    def __repr__(self):
        return "<%s>"%self.__class__.__name__

    def execute(self, commands):
        for p in commands:
            if self._scanchain and self._scanchain._debug:
                print("  Executing", p)#pragma: no cover

            if not hasattr(p, '_driver_function_name'):
                p.execute()
            else:
                func = getattr(self, p._driver_function_name, None)
                if not func:
                    raise Exception(
                        "Registered function %s not found on class %s"%\
                        (p._driver_function_name, p.__class__))

                args, kwargs = p._get_args()
                res = func(*args, **kwargs)
                if res and p._promise:
                    if self._scanchain and self._scanchain._debug:#pragma: no cover
                        print("RAW DATA GOING TO PROMISE", res, len(res))
                    p._promise._fulfill(res)

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
        pass

    def jtag_disable(self):
        pass
