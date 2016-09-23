#-*- coding: utf-8 -*-
import pytest
from bitarray import bitarray
from usb1 import USBErrorPipe, USBErrorOverflow
from proteusisc.jtagUtils import blen2Blen, buff2Blen,\
    build_byte_align_buff

from proteusisc.test_utils import FakeUSBDev, FakeXPCU1Handle,\
    MockPhysicalJTAGDevice

def test_controller_control_messages():
    h = FakeXPCU1Handle()

    #JTAG ON/OFF
    assert h.jtagon is False
    h.controlWrite(0x40, 0xB0, 0x18, 0, b'')
    assert h.jtagon is True
    h.controlWrite(0x40, 0xB0, 0x10, 0, b'')
    assert h.jtagon is False

    #RET CONSTANT
    res = h.controlRead(0xC0, 0xB0, 0x40, 0, 2)
    assert res == b'\xB5\x03'

    #VERSIONS
    res = h.controlRead(0xC0, 0xB0, 0x50, 0, 2)
    assert res == b'\x04\x04'
    res = h.controlRead(0xC0, 0xB0, 0x50, 1, 2)
    assert res == b'\x12\x34'
    res = h.controlRead(0xC0, 0xB0, 0x50, 2, 2)
    assert res == b'\x04\x00'
    res = h.controlRead(0xC0, 0xB0, 0x50, 3, 2)
    assert res == b'\x05\x06'

    #SPEED
    assert h.speed is 0x11
    h.controlWrite(0x40, 0xB0, 0x28, 0x14, b'')
    assert h.speed is 0x14

    with pytest.raises(Exception):
        h.controlWrite(0x40, 0xB0, 0x28, 0x04, b'')

    #REVERSE INDEX
    res = h.controlRead(0xC0, 0xB0, 0x20, 0xF1, 2)
    assert res == b'\x8F'


    #INVALID MESSAGES
    with pytest.raises(Exception):
        h.controlWrite(0x40, 0x00, 0x18, 0, b'')
    with pytest.raises(Exception):
        h.controlWrite(0x40, 0xB0, -1, 0, b'')
    with pytest.raises(Exception):
        h.controlWrite(0x40, 0xB0, 0, -1, b'')
    with pytest.raises(USBErrorPipe):
        h.controlWrite(0x40, 0xB0, 0, 0, b'')
    with pytest.raises(USBErrorPipe):
        h.controlRead(0xC0, 0xB0, 0, 0, 0)
    with pytest.raises(USBErrorOverflow):
        h.controlRead(0xC0, 0xB0, 0x50, 0, 1)

    #HAS A CLOSE METHOD
    h.close()

def test_jtag_transfer_simple_tms():
    d0 = MockPhysicalJTAGDevice(name="D0", status=bitarray('11111100'))
    h = FakeXPCU1Handle(d0)
    h.controlWrite(0x40, 0xB0, 0x18, 0, b'')

    h.controlWrite(0x40, 0xb0, 0xa6, 9-1, b'')
    h.bulkWrite(2, b'\xF0\x0F\x50\x0F\x00\x01')
    assert d0.tapstate == "SHIFTDR"

def test_jtag_transfer_simple_read_tro():
    d0 = MockPhysicalJTAGDevice(name="D0", status=bitarray('11111100'))
    h = FakeXPCU1Handle(d0)
    h.controlWrite(0x40, 0xB0, 0x18, 0, b'')

    h.controlWrite(0x40, 0xb0, 0xa6, 9-1, b'')
    h.bulkWrite(2, b'\xF0\x0F\x50\x0F\x00\x01')
    assert d0.tapstate == "SHIFTDR"

    h.controlWrite(0x40, 0xb0, 0xa6, 32-1, b'')
    h.bulkWrite(2, b'\x00\xFF\x00\xFF\x00\xFF\x00\xFF\x00\xFF\x00\xFF\x00\xFF\x00\xFF')
    res = h.bulkRead(6, 4)
    bits = bitarray()
    bits.frombytes(res)
    assert bits == d0._idcode


def test_jtag_transfer_simple_complex():
    d0 = MockPhysicalJTAGDevice(name="D0", status=bitarray('11111100'))
    h = FakeXPCU1Handle(d0)
    h.controlWrite(0x40, 0xB0, 0x18, 0, b'')

    #Transition to SHIFTDR, stop clocking for several cycles, read DR
    h.controlWrite(0x40, 0xb0, 0xa6, 32+16-1, b'')
    h.bulkWrite(2, b'\xF0\x0F\x50\x0F\x00\x01\x00\x00\x00\xFF\x00\xFF\x00\xFF\x00\xFF\x00\xFF\x00\xFF\x00\xFF\x00\xFF')
    res = h.bulkRead(6, 4)
    bits = bitarray()
    bits.frombytes(res)
    assert bits == d0._idcode

def test_jtag_transfer_errors():
    d0 = MockPhysicalJTAGDevice(name="D0", status=bitarray('11111100'))
    h = FakeXPCU1Handle(d0)
    h.controlWrite(0x40, 0xB0, 0x18, 0, b'')

    #INVALID BULK WRITE
    with pytest.raises(Exception):
        h.bulkWrite(0, b'\x00\x00') #WRONG ENDPOINT
    with pytest.raises(Exception):
        h.bulkWrite(2, b'\x00')# ODD DATA COUNT
    assert not h.doing_transfer
    with pytest.raises(Exception):
        h.bulkWrite(2, b'\x00\x00')#DATA WITHOUT TRANSFER STARTED

    #INVALID BULK READ
    with pytest.raises(Exception):
        h.bulkRead(0, 0) #WRONG ENDPOINT
    assert not h._blk_read_buffer
    with pytest.raises(Exception):
        h.bulkRead(6, 0) #No data

    #INCORRECT BYTE SIZE FOR WRITE
    h.controlWrite(0x40, 0xb0, 0xa6, 9-1, b'')
    with pytest.raises(Exception):
        h.bulkWrite(2, b'\xF0\x0F')
