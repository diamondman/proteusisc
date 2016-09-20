from bitarray import bitarray
# pylint: disable=no-name-in-module
from usb1 import USBErrorPipe, USBErrorOverflow

from ..drivers.digilentdriver import _CMSG_PROD_NAME, _CMSG_USER_NAME,\
    _CMSG_SERIAL_NO, _CMSG_FW_VER, _CMSG_DEV_CAPS, _CMSG_OEM_SEED,\
    _CMSG_PROD_ID, _CMSG_OEM_CHECK

class FakeDevHandle(object):
    """Artificial USB Digilent ISC controller that implements the usb1.USBDeviceHandle interface.

    With real USB ISC Controllers, a USBDevice can be used to get a
    Handle to th communicate with the physical device. But simulating
    the full USB subsysem, or hooking into it, is too much of a pain,
    so simulating a USB device is more easily done by just handling
    the application level USB library functions directly.

    FakeDevHandle is treated as a handle, but it is really the
    simulated USB device.

    Understanding the USB related functions of this class requires
    understanding libusb1.0 and USB in general, most ththe types of
    requests, what endpoints are, and what fields are required for
    each message type. The following links should be enough to get
    started:
        http://www.beyondlogic.org/usbnutshell/usb6.shtml
        https://github.com/vpelletier/python-libusb1/blob/master/usb1.py
        http://libusb.sourceforge.net/api-1.0/group__syncio.html#gadb11f7a761bd12fc77a07f4568d56f38

    """
    USB_VEND_ID = 0x1443
    USB_PROD_ID = 0x0007

    # Special Controller specific constants.
    PROD_NAME = b'CoolRunner 2 Starter 2'
    USER_NAME = b'Cr2s2'
    SERIAL_NO = b"10146D508907"
    FW_VER = b'\x1A\x01\x31\x30'#0x1A013130
    PROD_ID = b'\x00\x90\x01\x26'#'0x00900126
    DEV_CAP = b'\x00\x00\x00\x15'#0x00000015

    #Digilent controllers use a 4 byte bulk packet header to specify
    #what command will be run. This structure is a mappint of
    # (category, request) : (command_name, init_packet_length)
    BLK_HANDLERS = {
        (0x02, 0x00): ("ENABLE_JTAG", 0x03),
        (0x02, 0x01): ("DISABLE_JTAG", 0x03),
        (0x02, 0x02): ("PORT_INFO", 0x04),
        (0x02, 0x03): ("SET_SPEED", 0x07), #Returns error 4
        (0x02, 0x04): ("GET_SPEED", 0x03), #Returns error 4
        (0x02, 0x05): ("SET_TMS_TDI_TDO", 0x06),
        (0x02, 0x06): ("GET_TMS_TDI_TDO_TCK", 0x03),
        (0x02, 0x07): ("CLOCK_TICK", 0x09),
        (0x02, 0x08): ("WRITE_TDI", 0x09),
        (0x02, 0x09): ("READ_TDO", 0x09),
        (0x02, 0x0A): ("WRITE_TMS_TDI", 0x08),
        (0x02, 0x0B): ("WRITE_TMS", 0x09)
    }

    def __init__(self, *devices):
        self.devices = devices
        self._jtag_on = False
        self._oem_seed = b'\x00\x00'
        self._blk_read_buffer = []
        self._lastcmd = None
        self._adv_req_enabled = False

    @property
    def jtagon(self):
        """Check if the controller's JTAG enable bit is set"""
        return self._jtag_on

    def close(self):
        """Close the handle.

        This is required for real hardware, but for a simulation that
        is really just a controller, nothing has to happen. The
        function is required to comply with the usb1.USBDeviceHandle
        interface."""
        pass

    def controlWrite(self, request_type, request, value, index, data,
                     timeout=0):

        """Simulates libusb's synchronous control write in a sandbox.

        Only features explicitly used by the simulated controller's
        drier are implemented, so important USB management messages
        are not implemented.

        For details about this interface and arguments, refer to the
        links provided in the class description.

        For details on the commands supported by this simulated
        controller, please consult the controller doncumentation:
            http://diamondman.github.io/Adapt/cable_digilent_adept.html#control-messages

        Returns:
            An integer length of the number of bytes sent.

        """
        if request_type & 0x80 is not 0x00:
            raise Exception("Incorrect data direction in reqtype")

        if request is _CMSG_OEM_SEED:
            self._oem_seed = data

        return len(data)

    def controlRead(self, request_type, request, value, index, length,
                    timeout=0):
        """Simulates libusb's synchronous control read in a sandbox.

        Only features explicitly used by the simulated controller's
        drier are implemented, so important USB management messages
        are not implemented.

        For details about this interface and arguments, refer to the
        links provided in the class description.

        For details on the commands supported by this simulated
        controller, please consult the controller doncumentation:
            http://diamondman.github.io/Adapt/cable_digilent_adept.html#control-messages

        Returns:
            A bytes buffer containing the data read from the controller.
            #TODO Add details about format to docstring or documentation.
        """
        if request_type & 0x80 is not 0x80:
            raise Exception("Incorrect data direction in reqtype")

        if request is _CMSG_PROD_NAME:
            res =  self.PROD_NAME
        elif request is _CMSG_USER_NAME:
            res =  self.USER_NAME
        elif request is _CMSG_SERIAL_NO:
            res =  self.SERIAL_NO
        elif request is _CMSG_FW_VER:
            res =  self.FW_VER[:length]
        elif request is _CMSG_DEV_CAPS:
            res =  self.DEV_CAP
        elif request is _CMSG_PROD_ID:
            res =  self.PROD_ID
        elif request is _CMSG_OEM_CHECK:
            oembyte = self._oem_seed[0]^self._oem_seed[1]
            res =  bytes((oembyte^ord(b) for b in reversed('Digi')))
        else:
            raise USBErrorPipe(-9)

        print(res, length)
        if len(res)>length:
            raise USBErrorOverflow(-8)
        return res

    def bulkWrite(self, endpoint, data, timeout=0):
        """Simulates libusb's synchronous bulk write in a sandbox.

        Almost all RPC calls to the Digilent JTAG controller are
        started with a bulk write. The message contains a length, a
        cateory, a command, and optional parameters. The format of the
        initialization request is described at:
            http://diamondman.github.io/Adapt/cable_digilent_adept.html#bulk-requests

        This function has to update the state of the 'controller' so
        further messages can finish the RPC request. Each command can
        have a unique sequence of messages, so each command is handled
        with its own function .

        For example, if a message came in starting with
            0x09 02 0B 00

        The category is 2, and the command is 0x0B. In the table
        'BLK_HANDLERS', (2, 0xB) maps to ("WRITE_TMS", 9) which is the
        name and required length. The required length field matches,
        so the function _handle_blk_WRITE_TMS will be called.

        The WRITE_TMS handler will decode all the RPC specific
        parameters, and prepare the simulated device for the next
        write stage. A status message (2 bytes) will also be added to
        the return buffer to be retrieved on the next read.

        The next bulk write will be treated as the data stage of the
        Digilent 'advanced transfer protocol' specified in the above
        controller documentation link. This requrest will be handled
        by the stage2 handler for WRITE_TMS:
            _handle_blk_WRITE_TMS_stage2

        If data was requested to be returned, it will be put on the
        return buffer to be read later.

        Finally, statistics on the last operation may be requested by
        setting the 7th bit of Request to 1. These statistics will be
        put on the return buffer and can be read out later.

        """

        if not self._adv_req_enabled:
            if len(data) < 4:
                raise Exception("Too short message. Min 4 bytes")

            length, cat, req, params = data[0], data[1], data[2], data[4:]
            if req & 0x80 is 0x80:
                self._report_advanced_metrics()
            else:
                if length+1 is not len(data):
                    raise Exception("Length does not match header; "
                                    "length: %s; Payload len: %s"%
                                    (length, len(data)-1))

                self._lastcmd = (cat, req)
                name, length_req = self.BLK_HANDLERS.get((cat, req),
                                                         (None, None))
                #if name is None:
                #    #TODO MAKE RESPOND WITH STALL
                if length is not length_req:
                    raise Exception("Wrong Length for instruction. "
                                    "Would Hang")

                handler_name = "_handle_blk_"+name
                handler = getattr(self, handler_name, None)
                if not handler:
                    raise Exception("No handler %s. Would Stall."%
                                    handler_name) # pragma: no cover

                #print("BEFOREEXEC %s******"%name, self._blk_read_buffer)
                handler(params)
                #print("AFTER EXEC******", self._blk_read_buffer)
        else:
            #For Advanced messages, there is no header, just raw data.
            self._adv_req_enabled = False
            name, _ = self.BLK_HANDLERS[self._lastcmd]
            handler_name = "_handle_blk_"+name+"_stage2"
            handler = getattr(self, handler_name)
            res = handler(data, self._adv_req_bitcount,
                          self._adv_req_read_tdo,
                          **self._adv_req_extra_params)

    def bulkRead(self, endpoint, length, timeout=0):
        if self._blk_read_buffer:
            #print("BEFORE READ******", self._blk_read_buffer)
            res = self._blk_read_buffer[0]
            del self._blk_read_buffer[0]
            #print("AFTER READ******", self._blk_read_buffer)
            return res
        raise Exception("Would Hang waiting for something to return")

    def _report_advanced_metrics(self):
        """Report the metrics of the last RPC.

        Digilent RPCs can be followed up with a call to check the
        statistics of the last command. This includes the number of
        bits writte, if a read happened, and the number of bits read
        (only if a read did occur).

        When called, this puts the metrics packet in the response
        buffer for retrieval on a future read..

        """
        sz = 1 + 4 + (4*bool(self._adv_req_read_tdo))
        flags = 0x80 + (0x40 if self._adv_req_read_tdo else 0)
        writecount = self._adv_req_bitcount.to_bytes(4, 'little')
        readcount = self._adv_req_bitcount.to_bytes(4, 'little')\
                    if self._adv_req_read_tdo else b''
        self._blk_read_buffer.append(
            b'%c%c'%(sz, flags) + writecount\
            + readcount)

    def _write_to_dev_chain(self, tms, tdi):
        """Simulate electrically asserting a bit to the JTAG output pins.

        Args:
            tms: A boolean to be asserted to every simulated device's
             (in the chain) tms bit.
            tdi: A boolean to be shifted into the first simulated
             device's tdi pin.

        Returns:
            The boolean read from the tdo pin of the last device in
            the scan chain

        """
        #oldstate = self.devices[0].tap.state
        for dev in self.devices:
            tdi = dev.shift(tms, tdi)
        #print("State %s => %s; Reading %s"%
        #    (oldstate,self.devices[0].tap.state,tdi))
        return tdi

    def _initialize_advanced_return(self, bitcount, read_tdo,
                                    **params):
        """Helper method to assign some important values to keep track of Digilent controller state."""
        self._adv_req_enabled = True
        self._adv_req_bitcount = bitcount
        self._adv_req_read_tdo = read_tdo
        self._adv_req_extra_params = params

    def _handle_blk_ENABLE_JTAG(self, params):
        if self._jtag_on:
            self._blk_read_buffer.append(b'\x01\x03')
        else:
            self._jtag_on = True
            self._blk_read_buffer.append(b'\x01\x00')

    def _handle_blk_DISABLE_JTAG(self, params):
        self._jtag_on = False
        self._blk_read_buffer.append(b'\x01\x00')

    def _handle_blk_WRITE_TMS_TDI(self, params):
        doreturn = bool(params[0])
        bitcount = sum([b<<(i*8) for i,b in enumerate(params[1:5])])
        self._initialize_advanced_return(bitcount, doreturn)
        self._blk_read_buffer.append(b'\x01\x00')
    def _handle_blk_WRITE_TMS_TDI_stage2(self, data, bitcount, read_tdo):
        bits = bitarray()
        bits.frombytes(data[::-1])
        bits = bits[(8*len(data)) - (bitcount*2):]
        tms = bits[::2][::-1]
        tdi = bits[1::2][::-1]
        tdo = []
        for i in range(bitcount):
            tdo.append(self._write_to_dev_chain(tms[i], tdi[i]))
        if read_tdo:
            tdo_bits = bitarray(([False]*(8-(len(tdo)%8)))+tdo[::-1])
            tdo_bytes = tdo_bits.tobytes()
            self._blk_read_buffer.append(tdo_bytes[::-1])

    def _handle_blk_WRITE_TMS(self, params):
        doreturn = bool(params[0])
        tdi = params[1]
        bitcount = sum([b<<(i*8) for i,b in enumerate(params[2:6])])
        self._initialize_advanced_return(bitcount, doreturn, tdi=tdi)
        self._blk_read_buffer.append(b'\x01\x00')
    def _handle_blk_WRITE_TMS_stage2(self, data, bitcount,
                                     read_tdo, *, tdi):
        bits = bitarray()
        bits.frombytes(data[::-1])
        tms = bits[(8*len(data)) - (bitcount):]
        tdo = []
        for tmsbit in reversed(tms):
            tdo.append(self._write_to_dev_chain(tmsbit, tdi))
        if read_tdo:
            tdo_bits = bitarray(([False]*(8-(len(tdo)%8)))+tdo[::-1])
            tdo_bytes = tdo_bits.tobytes()
            self._blk_read_buffer.append(tdo_bytes[::-1])

    def _handle_blk_READ_TDO(self, params):
        tms = params[0]
        tdi = params[1]
        bitcount = sum([b<<(i*8) for i,b in enumerate(params[2:6])])
        tdo = []
        for i in range(bitcount):
            tdo.append(self._write_to_dev_chain(tms, tdi))

        self._adv_req_bitcount = bitcount
        self._adv_req_read_tdo = True
        self._blk_read_buffer.append(b'\x01\x00')
        tdo_bits = bitarray(([False]*(8-(len(tdo)%8)))+tdo[::-1])
        tdo_bytes = tdo_bits.tobytes()
        self._blk_read_buffer.append(tdo_bytes[::-1])

    def _handle_blk_WRITE_TDI(self, params):
        doreturn = bool(params[0])
        tms = params[1]
        bitcount = sum([b<<(i*8) for i,b in enumerate(params[2:6])])
        self._initialize_advanced_return(bitcount, doreturn, tms=tms)
        self._blk_read_buffer.append(b'\x01\x00')
    def _handle_blk_WRITE_TDI_stage2(self, data, bitcount,
                                     read_tdo, *, tms):
        bits = bitarray()
        bits.frombytes(data[::-1])
        tdi = bits[(8*len(data)) - (bitcount):]
        print(tdi)
        tdo = []
        for tdibit in reversed(tdi):
            tdo.append(self._write_to_dev_chain(tms, tdibit))
        if read_tdo:
            tdo_bits = bitarray(([False]*(8-(len(tdo)%8)))+tdo[::-1])
            tdo_bytes = tdo_bits.tobytes()
            self._blk_read_buffer.append(tdo_bytes[::-1])

class FakeUSBDev(object):
    """The most basic features required for simulating a usb1.USBDevice.

    Normally, a usb1.USBDevice is retrieved with:
        >>> import usb1
        >>> context = usb1.USBContext()
        >>> dev = context.getDeviceList()[0]

    The USBDevice only is used to check ids to match a driver, and
    open a handle (type usb1.USBDeviceHandle) that can be used to talk
    to the physical device.  The handle is retrieved from the
    USBDevice with the open method:
        >>> handle = dev.open()
        >>> handle.controlWrite(........) #DO USB THINGS

    A real USBDevice must track many states and pointers to usb
    resources, including managing open handles. A fake USBDevice only
    has to provide a handle when open is called, and report the
    appropriate vendorID and productID.

    Attributes:
        ctrl_handle: An implementation of the usb1.USBDeviceHandle
        interface that will be returned when the FakeUSBDev's open()
        method is called.

    """
    def __init__(self, mockPhysicalController):
        self.ctrl_handle = mockPhysicalController
    def open(self):
        return self.ctrl_handle
    def getVendorID(self):
        return type(self.ctrl_handle).USB_VEND_ID
    def getProductID(self):
        return type(self.ctrl_handle).USB_PROD_ID
