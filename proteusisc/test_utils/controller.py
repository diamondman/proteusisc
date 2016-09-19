from bitarray import bitarray
from usb1 import USBErrorPipe, USBErrorOverflow

from ..drivers.digilentdriver import _CMSG_PROD_NAME, _CMSG_USER_NAME,\
    _CMSG_SERIAL_NO, _CMSG_FW_VER, _CMSG_DEV_CAPS, _CMSG_OEM_SEED,\
    _CMSG_PROD_ID, _CMSG_OEM_CHECK

class FakeDevHandle(object):
    USB_VEND_ID = 0x1443
    USB_PROD_ID = 0x0007

    PROD_NAME = b'CoolRunner 2 Starter 2'
    USER_NAME = b'Cr2s2'
    SERIAL_NO = b"10146D508907"
    FW_VER = b'\x1A\x01\x31\x30'#0x1A013130
    PROD_ID = b'\x00\x90\x01\x26'#'0x00900126
    DEV_CAP = b'\x00\x00\x00\x15'#0x00000015

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
        self._blk_read_buffer2 = []
        self._lastcmd = None
        self._adv_req_enabled = False

    def close(self):
        pass

    def controlWrite(self, request_type, request, value, index, data,
                     timeout=0):
        if request_type & 0x80 is not 0x00:
            raise Exception("Incorrect data direction in reqtype")

        if request is _CMSG_OEM_SEED:
            self._oem_seed = data

    def controlRead(self, request_type, request, value, index, length,
                    timeout=0):
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
        if not self._adv_req_enabled:
            length, cat, req, params = data[0], data[1], data[2], data[4:]
            if req & 0x80 is 0x80:
                self._report_advanced_metrics()
            else:
                if length+1 is not len(data):
                    raise Exception("Length does not match header; "
                                    "length: %s; Payload len: %s"%
                                    (length, len(data)-1))

                self._lastcmd = (cat, req)
                name, length_req = self.BLK_HANDLERS[(cat, req)]
                if length is not length_req:
                    raise Exception("Wrong Length for instruction. "
                                    "Would Hang")

                handler_name = "_handle_blk_"+name
                handler = getattr(self, handler_name, None)
                if not handler:
                    raise Exception("No handler %s. Would Stall."%
                                    handler_name)

                #print("BEFOREEXEC %s******"%name, self._blk_read_buffer2)
                handler(params)
                #print("AFTER EXEC******", self._blk_read_buffer2)
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
        if self._blk_read_buffer2:
            #print("BEFORE READ******", self._blk_read_buffer2)
            res = self._blk_read_buffer2[0]
            del self._blk_read_buffer2[0]
            #print("AFTER READ******", self._blk_read_buffer2)
            return res
        raise Exception("Would Hang waiting for something to return")

    def _report_advanced_metrics(self):
        #Return metrics
        sz = 1 + 4 + (4*bool(self._adv_req_read_tdo))
        flags = 0x80 + (0x40 if self._adv_req_read_tdo else 0)
        writecount = self._adv_req_bitcount.to_bytes(4, 'little')
        readcount = self._adv_req_bitcount.to_bytes(4, 'little')\
                    if self._adv_req_read_tdo else b''
        self._blk_read_buffer2.append(
            b'%c%c'%(sz, flags) + writecount\
            + readcount)

    def _write_to_dev_chain(self, tms, tdi):
        #oldstate = self.devices[0].tap.state
        for dev in self.devices:
            tdi = dev.shift(tms, tdi)
        #print("State %s => %s; Reading %s"%
        #    (oldstate,self.devices[0].tap.state,tdi))
        return tdi

    def _initialize_advanced_return(self, bitcount, read_tdo,
                                    **params):
        self._adv_req_enabled = True
        self._adv_req_bitcount = bitcount
        self._adv_req_read_tdo = read_tdo
        self._adv_req_extra_params = params

    def _handle_blk_ENABLE_JTAG(self, params):
        if self._jtag_on:
            self._blk_read_buffer2.append(b'\x01\x03')
        else:
            self._jtag_on = True
            self._blk_read_buffer2.append(b'\x01\x00')

    def _handle_blk_DISABLE_JTAG(self, params):
        self._jtag_on = False
        self._blk_read_buffer2.append(b'\x01\x00')

    def _handle_blk_WRITE_TMS_TDI(self, params):
        doreturn = bool(params[0])
        bitcount = sum([b<<(i*8) for i,b in enumerate(params[1:5])])
        self._initialize_advanced_return(bitcount, doreturn)
        self._blk_read_buffer2.append(b'\x01\x00')
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
            self._blk_read_buffer2.append(tdo_bytes[::-1])

    def _handle_blk_WRITE_TMS(self, params):
        doreturn = bool(params[0])
        tdi = params[1]
        bitcount = sum([b<<(i*8) for i,b in enumerate(params[2:6])])
        self._initialize_advanced_return(bitcount, doreturn, tdi=tdi)
        self._blk_read_buffer2.append(b'\x01\x00')
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
            self._blk_read_buffer2.append(tdo_bytes[::-1])

    def _handle_blk_READ_TDO(self, params):
        tms = params[0]
        tdi = params[1]
        bitcount = sum([b<<(i*8) for i,b in enumerate(params[2:6])])
        tdo = []
        for i in range(bitcount):
            tdo.append(self._write_to_dev_chain(tms, tdi))

        self._adv_req_bitcount = bitcount
        self._adv_req_read_tdo = True
        self._blk_read_buffer2.append(b'\x01\x00')
        tdo_bits = bitarray(([False]*(8-(len(tdo)%8)))+tdo[::-1])
        tdo_bytes = tdo_bits.tobytes()
        self._blk_read_buffer2.append(tdo_bytes[::-1])

    def _handle_blk_WRITE_TDI(self, params):
        doreturn = bool(params[0])
        tms = params[1]
        bitcount = sum([b<<(i*8) for i,b in enumerate(params[2:6])])
        self._initialize_advanced_return(bitcount, doreturn, tms=tms)
        self._blk_read_buffer2.append(b'\x01\x00')
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
            self._blk_read_buffer2.append(tdo_bytes[::-1])

class FakeUSBDev(object):
    def __init__(self, mockPhysicalController):
        self.ctrl_handle = mockPhysicalController
    def open(self):
        return self.ctrl_handle
    def getVendorID(self):
        return type(self.ctrl_handle).USB_VEND_ID
    def getProductID(self):
        return type(self.ctrl_handle).USB_PROD_ID
