#-*- coding: utf-8 -*-
import pytest
from bitarray import bitarray
from usb1 import USBErrorPipe, USBErrorOverflow
from proteusisc.jtagUtils import blen2Blen, buff2Blen,\
    build_byte_align_buff

from proteusisc.test_utils import FakeUSBDev, FakeDevHandle,\
    MockPhysicalJTAGDevice
from proteusisc.drivers.digilentdriver import _CMSG_PROD_NAME,\
    _CMSG_USER_NAME, _CMSG_SERIAL_NO, _CMSG_FW_VER, _CMSG_DEV_CAPS,\
    _CMSG_OEM_SEED, _CMSG_PROD_ID, _CMSG_OEM_CHECK,\
    _BMSG_ENABLE_JTAG, _BMSG_DISABLE_JTAG, _BMSG_WRITE_TMS,\
    _BMSG_WRITE_TMS_TDI, _BMSG_WRITE_TDI, _BMSG_READ_TDO,\
    _BMSG_CLOCK_TICK
def test_fakeusbdev():
    ctrl = FakeDevHandle()
    usbdev = FakeUSBDev(ctrl)
    assert usbdev.open() == ctrl
    assert usbdev.getVendorID() == ctrl.USB_VEND_ID
    assert usbdev.getProductID() == ctrl.USB_PROD_ID

def test_controller_control_messages():
    h = FakeDevHandle()

    with pytest.raises(Exception):
        h.controlRead(0x40, 0, 0, 0, 0)
    with pytest.raises(Exception):
        h.controlWrite(0xC0, 0, 0, 0, 0)

    with pytest.raises(USBErrorPipe):
        h.controlRead(0xC0, 1, 0, 0, 0, 0)
    with pytest.raises(USBErrorOverflow):
        h.controlRead(0xC0, _CMSG_PROD_NAME, 0, 0, 0, 1)

    res = h.controlRead(0xC0, _CMSG_PROD_NAME, 0, 0, 28)
    val =  FakeDevHandle.PROD_NAME
    assert res == val
    res = h.controlRead(0xC0, _CMSG_USER_NAME, 0, 0, 16)
    val =  FakeDevHandle.USER_NAME
    assert res == val
    res = h.controlRead(0xC0, _CMSG_SERIAL_NO, 0, 0, 12)
    val =  FakeDevHandle.SERIAL_NO
    assert res == val
    res = h.controlRead(0xC0, _CMSG_FW_VER, 0, 0, 2)
    val =  FakeDevHandle.FW_VER[:2]
    assert res == val
    res = h.controlRead(0xC0, _CMSG_DEV_CAPS, 0, 0, 4)
    val =  FakeDevHandle.DEV_CAP
    assert res == val
    res = h.controlRead(0xC0, _CMSG_PROD_ID, 0, 0, 4)
    val =  FakeDevHandle.PROD_ID
    assert res == val

    oem_seed = b'0x12\x34'
    h.controlWrite(0x40, _CMSG_OEM_SEED, 0, 0, oem_seed)
    res = h.controlRead(0xC0, _CMSG_OEM_CHECK, 0, 0, 4)
    oembyte = oem_seed[0]^oem_seed[1]
    val =  bytes((oembyte^ord(b) for b in reversed('Digi')))
    assert res == val

def test_controller_close():
    #Nothing here yet....
    h = FakeDevHandle()
    h.close()

def test_controller_bulk_read_no_data():
    h = FakeDevHandle()
    with pytest.raises(Exception):
        h.bulkRead(2, 2)

def test_controller_bulk_msg_wrong_size_init():
    h = FakeDevHandle()
    with pytest.raises(Exception):
        #WRITE TMS requires 6 additional bytes of data
        h.bulkWrite(1, _BMSG_WRITE_TMS)
    with pytest.raises(Exception):
        #Incorrect packet length
        h.bulkWrite(1, b'\x08\x00\x00\x00')
    with pytest.raises(Exception):
        #INCORRECT LENGTH FOR COMMAND
        h.bulkWrite(1, b'\x03\x02\x0A\x00')

def test_controller_bulk_msg_wrong_length_header_field():
    h = FakeDevHandle()
    with pytest.raises(Exception):
        #WRITE TMS requires 6 additional bytes of data
        h.bulkWrite(1, b'\x08\x00')


def test_controller_jtag_on_off():
    h = FakeDevHandle()
    assert not h.jtagon

    #Turn it on
    h.bulkWrite(1, _BMSG_ENABLE_JTAG)
    res = h.bulkRead(2, 2)
    assert res == b'\x01\x00'
    assert h.jtagon

    #Turn it off
    h.bulkWrite(1, _BMSG_DISABLE_JTAG)
    res = h.bulkRead(2, 2)
    assert res == b'\x01\x00'
    assert not h.jtagon

    #Turn it on again
    h.bulkWrite(1, _BMSG_ENABLE_JTAG)
    res = h.bulkRead(2, 2)
    assert res == b'\x01\x00'
    assert h.jtagon

    #turn it on again without turning it off first
    h.bulkWrite(1, _BMSG_ENABLE_JTAG)
    res = h.bulkRead(2, 2)
    assert res == b'\x01\x03' #FAILED, but that is ok.
    assert h.jtagon


def test_controller_write_tms():
    d0 = MockPhysicalJTAGDevice(name="D0", status=bitarray('11111100'))
    h = FakeDevHandle(d0)

    #ENABLE JTAG
    h.bulkWrite(1, _BMSG_ENABLE_JTAG)
    res = h.bulkRead(2, 2)
    assert res == b'\x01\x00'

    #WRITE TMS to change TAP to SHIFTDR
    h.bulkWrite(1, _BMSG_WRITE_TMS + b'\x00\x00\x09\x00\x00\x00')
    res = h.bulkRead(2, 2)
    assert res == b'\x01\x00'

    data = bitarray('001011111')
    h.bulkWrite(3, build_byte_align_buff(data).tobytes()[::-1])
    assert d0.tapstate == "SHIFTDR"

    h.bulkWrite(4, bytes([0x03, 0x02, 0x8B, 0x00]))
    res = h.bulkRead(2, 6)
    assert res == b'\x05\x80\x09\x00\x00\x00'

    ################################################
    #READ DR
    ################################################
    h.bulkWrite(1, _BMSG_WRITE_TMS + b'\x01\x01\x20\x00\x00\x00')
    res = h.bulkRead(2, 2)
    assert res == b'\x01\x00'

    data = bitarray('1'+('0'*31))
    h.bulkWrite(3, build_byte_align_buff(data).tobytes()[::-1])
    assert d0.tapstate == "EXIT1DR"

    tdo_bytes = h.bulkRead(4, buff2Blen(data))[::-1]
    tdo_bits = bitarray()
    tdo_bits.frombytes(tdo_bytes)
    tdo_bits = tdo_bits[(8*len(tdo_bytes)) - len(data):]
    assert tdo_bits == d0.idcode

    h.bulkWrite(4, bytes([0x03, 0x02, 0x8B, 0x00]))
    res = h.bulkRead(2, 6)
    assert res == b'\t\xc0\x20\x00\x00\x00\x20\x00\x00\x00'

def test_controller_write_tms_tdi():
    d0 = MockPhysicalJTAGDevice(name="D0", status=bitarray('11111100'))
    h = FakeDevHandle(d0)

    #ENABLE JTAG
    h.bulkWrite(1, _BMSG_ENABLE_JTAG)
    res = h.bulkRead(2, 2)
    assert res == b'\x01\x00'

    #WRITE TMS to change TAP to SHIFTDR
    h.bulkWrite(1, _BMSG_WRITE_TMS_TDI + b'\x00\x09\x00\x00\x00')
    res = h.bulkRead(2, 2)
    assert res == b'\x01\x00'

    tmsdata = bitarray('001011111')
    tdidata = bitarray('000000000')
    data = bitarray([val for pair in zip(tmsdata, tdidata)
                     for val in pair])
    h.bulkWrite(3, build_byte_align_buff(data).tobytes()[::-1])
    assert d0.tapstate == "SHIFTDR"

    h.bulkWrite(4, bytes([0x03, 0x02, 0x8A, 0x00]))
    res = h.bulkRead(2, 6)
    assert res == b'\x05\x80\x09\x00\x00\x00'

    ################################################
    #READ DR
    ################################################
    h.bulkWrite(1, _BMSG_WRITE_TMS_TDI + b'\x01\x20\x00\x00\x00')
    res = h.bulkRead(2, 2)
    assert res == b'\x01\x00'

    tmsdata = bitarray('1'+('0'*31))
    tdidata = bitarray('0'*32)
    data = bitarray([val for pair in zip(tmsdata, tdidata)
                     for val in pair])
    h.bulkWrite(3, build_byte_align_buff(data).tobytes()[::-1])
    assert d0.tapstate == "EXIT1DR"

    tdo_bytes = h.bulkRead(4, buff2Blen(data))[::-1]
    tdo_bits = bitarray()
    tdo_bits.frombytes(tdo_bytes)
    tdo_bits = tdo_bits[(8*len(tdo_bytes)) - len(tmsdata):]
    assert tdo_bits == d0.idcode

    h.bulkWrite(4, bytes([0x03, 0x02, 0x8A, 0x00]))
    res = h.bulkRead(2, 6)
    assert res == b'\t\xc0\x20\x00\x00\x00\x20\x00\x00\x00'

def test_controller_write_tdi():
    d0 = MockPhysicalJTAGDevice(name="D0", status=bitarray('11111100'))
    h = FakeDevHandle(d0)

    #ENABLE JTAG
    h.bulkWrite(1, _BMSG_ENABLE_JTAG)
    res = h.bulkRead(2, 2)
    assert res == b'\x01\x00'

    #WRITE TMS to change TAP to SHIFTDR
    h.bulkWrite(1, _BMSG_WRITE_TMS + b'\x00\x00\x09\x00\x00\x00')
    res = h.bulkRead(2, 2)
    assert res == b'\x01\x00'

    data = bitarray('001011111')
    h.bulkWrite(3, build_byte_align_buff(data).tobytes()[::-1])
    assert d0.tapstate == "SHIFTDR"

    h.bulkWrite(4, bytes([0x03, 0x02, 0x8B, 0x00]))
    res = h.bulkRead(2, 6)
    assert res == b'\x05\x80\x09\x00\x00\x00'

    ################################################
    #READ DR WITH WRITE_TDI
    ################################################
    h.bulkWrite(1, _BMSG_WRITE_TDI + b'\x01\x00\x20\x00\x00\x00')
    res = h.bulkRead(2, 2)
    assert res == b'\x01\x00'

    data = bitarray('0'*32)
    h.bulkWrite(3, build_byte_align_buff(data).tobytes()[::-1])
    assert d0.tapstate == "SHIFTDR"

    tdo_bytes = h.bulkRead(4, buff2Blen(data))[::-1]
    tdo_bits = bitarray()
    tdo_bits.frombytes(tdo_bytes)
    tdo_bits = tdo_bits[(8*len(tdo_bytes)) - len(data):]
    assert tdo_bits == d0.idcode

    h.bulkWrite(4, bytes([0x03, 0x02, 0x88, 0x00]))
    res = h.bulkRead(2, 6)
    assert res == b'\t\xc0\x20\x00\x00\x00\x20\x00\x00\x00'

def test_controller_read_tdo():
    d0 = MockPhysicalJTAGDevice(name="D0", status=bitarray('11111100'))
    h = FakeDevHandle(d0)

    #ENABLE JTAG
    h.bulkWrite(1, _BMSG_ENABLE_JTAG)
    res = h.bulkRead(2, 2)
    assert res == b'\x01\x00'

    #WRITE TMS to change TAP to SHIFTDR
    h.bulkWrite(1, _BMSG_WRITE_TMS + b'\x00\x00\x09\x00\x00\x00')
    res = h.bulkRead(2, 2)
    assert res == b'\x01\x00'

    data = bitarray('001011111')
    h.bulkWrite(3, build_byte_align_buff(data).tobytes()[::-1])
    assert d0.tapstate == "SHIFTDR"

    h.bulkWrite(4, bytes([0x03, 0x02, 0x8B, 0x00]))
    res = h.bulkRead(2, 6)
    assert res == b'\x05\x80\x09\x00\x00\x00'

    ################################################
    #READ DR WITH READ_TDO
    ################################################
    h.bulkWrite(1, _BMSG_READ_TDO + b'\x00\x01\x20\x00\x00\x00')
    res = h.bulkRead(2, 2)
    assert res == b'\x01\x00'

    assert d0.tapstate == "SHIFTDR"

    tdo_bytes = h.bulkRead(4, 4)[::-1]
    tdo_bits = bitarray()
    tdo_bits.frombytes(tdo_bytes)
    tdo_bits = tdo_bits[(8*len(tdo_bytes)) - 32:]
    assert tdo_bits == d0.idcode

    h.bulkWrite(4, bytes([0x03, 0x02, 0x89, 0x00]))
    res = h.bulkRead(2, 6)
    assert res == b'\t\xc0\x20\x00\x00\x00\x20\x00\x00\x00'

def test_controller_clock_tick():
    d0 = MockPhysicalJTAGDevice(name="D0", status=bitarray('11111100'))
    h = FakeDevHandle(d0)

    #ENABLE JTAG
    h.bulkWrite(1, _BMSG_ENABLE_JTAG)
    res = h.bulkRead(2, 2)
    assert res == b'\x01\x00'

    #WRITE TMS to change TAP to SHIFTDR
    h.bulkWrite(1, _BMSG_CLOCK_TICK + b'\x01\x00\x05\x00\x00\x00')
    res = h.bulkRead(2, 2)
    assert res == b'\x01\x00'
    assert d0.tapstate == "TLR"

    h.bulkWrite(1, _BMSG_CLOCK_TICK + b'\x00\x00\x01\x00\x00\x00')
    res = h.bulkRead(2, 2)
    assert res == b'\x01\x00'
    assert d0.tapstate == "RTI"
