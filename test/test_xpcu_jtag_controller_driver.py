#-*- coding: utf-8 -*-
import pytest
from bitarray import bitarray

from proteusisc.controllerManager import getDriverInstanceForDevice
from proteusisc.test_utils import FakeUSBDev, FakeXPCU1Handle,\
    MockPhysicalJTAGDevice
from proteusisc.primitive import ConstantBitarray

def test_jtag_onoff():
    ctrl = FakeXPCU1Handle()
    c = getDriverInstanceForDevice(FakeUSBDev(ctrl))

    assert not ctrl.jtagon
    c.jtag_enable()
    assert ctrl.jtagon
    c.jtag_disable()
    assert not ctrl.jtagon

def test_xpcu_GPIO_transfer():
    d0 = MockPhysicalJTAGDevice(name="D0", status=bitarray('11111100'),
                    idcode=bitarray('00000110110101001000000010010011'))
    ctrl = FakeXPCU1Handle(d0)
    c = getDriverInstanceForDevice(FakeUSBDev(ctrl))
    c.jtag_enable()

    #RESET TAP AND TRANS TO SHIFTDR
    c.xpcu_GPIO_transfer(9-1, b'\xF0\x0F\x50\x0F\x00\x01')
    assert d0.tapstate == "SHIFTDR"

    #READ 32 BITS OF DATA
    bits = c.xpcu_GPIO_transfer(32-1, b'\x00\xFF\x00\xFF\x00\xFF\x00\xFF\x00\xFF\x00\xFF\x00\xFF\x00\xFF')
    assert d0.tapstate == "SHIFTDR"
    assert bits == d0._idcode

def test_xpcu_GPIO_transfer_adv():
    d0 = MockPhysicalJTAGDevice(name="D0", status=bitarray('11111100'),
                    idcode=bitarray('00000110110101001000000010010011'))
    ctrl = FakeXPCU1Handle(d0)
    c = getDriverInstanceForDevice(FakeUSBDev(ctrl))
    c.jtag_enable()

    #RESET, TRANS TO SHIFTDR, DO NOTHING, READ 32 BITS
    bits = c.xpcu_GPIO_transfer(32+16-1, b'\xF0\x0F\x50\x0F\x00\x01\x00\x00\x00\xFF\x00\xFF\x00\xFF\x00\xFF\x00\xFF\x00\xFF\x00\xFF\x00\xFF')
    assert d0.tapstate == "SHIFTDR"
    assert bits == d0._idcode

def test_xpcu_GPIO_transfer_adv_read_7_8_9_15_16_17_bits():
    #After reading 32 bits of data into a 2 to 4 byte little endian
    #number, the XPCU produces a new little endian shift register of
    #size 16 bits. This 2nd register can expand to 32 bits. There were
    #early issues with processing return data as it crossed boundaries.
    d0 = MockPhysicalJTAGDevice(name="D0", status=bitarray('11111100'),
                    idcode=bitarray('00000110110101001000000010010011'))
    ctrl = FakeXPCU1Handle(d0)
    c = getDriverInstanceForDevice(FakeUSBDev(ctrl))
    c.jtag_enable()
    #Do nothing interesting and read each bit. Checking return length
    ret = c.xpcu_GPIO_transfer(7-1, b'\x00\xFF'*2)
    assert len(ret) == 7

    ret = c.xpcu_GPIO_transfer(8-1, b'\x00\xFF'*2)
    assert len(ret) == 8

    ret = c.xpcu_GPIO_transfer(9-1, b'\x00\xFF'*3)
    assert len(ret) == 9

    ret = c.xpcu_GPIO_transfer(15-1, b'\x00\xFF'*4)
    assert len(ret) == 15

    ret = c.xpcu_GPIO_transfer(16-1, b'\x00\xFF'*4)
    assert len(ret) == 16

    ret = c.xpcu_GPIO_transfer(17-1, b'\x00\xFF'*5)
    assert len(ret) == 17

def test_xpcu_GPIO_transfer_adv_read_31_32_33_63_64_65_bits():
    #After reading 32 bits of data into a 2 to 4 byte little endian
    #number, the XPCU produces a new little endian shift register of
    #size 16 bits. This 2nd register can expand to 32 bits. There were
    #early issues processing return data as it crossed boundary.
    d0 = MockPhysicalJTAGDevice(name="D0", status=bitarray('11111100'),
                    idcode=bitarray('00000110110101001000000010010011'))
    ctrl = FakeXPCU1Handle(d0)
    c = getDriverInstanceForDevice(FakeUSBDev(ctrl))
    c.jtag_enable()
    #Do nothing interesting and read each bit. Checking return length
    ret = c.xpcu_GPIO_transfer(31-1, b'\x00\xFF'*8)
    assert len(ret) == 31

    ret = c.xpcu_GPIO_transfer(32-1, b'\x00\xFF'*8)
    assert len(ret) == 32

    ret = c.xpcu_GPIO_transfer(33-1, b'\x00\xFF'*9)
    assert len(ret) == 33

    ret = c.xpcu_GPIO_transfer(63-1, b'\x00\xFF'*16)
    assert len(ret) == 63

    ret = c.xpcu_GPIO_transfer(64-1, b'\x00\xFF'*16)
    assert len(ret) == 64

    ret = c.xpcu_GPIO_transfer(65-1, b'\x00\xFF'*17)
    assert len(ret) == 65

def test_transfer_bits():
    d0 = MockPhysicalJTAGDevice(name="D0", status=bitarray('11111100'),
                    idcode=bitarray('00000110110101001000000010010011'))
    ctrl = FakeXPCU1Handle(d0)
    c = getDriverInstanceForDevice(FakeUSBDev(ctrl))
    c.jtag_enable()

    #RESET TAP AND TRANS TO SHIFTDR
    c.transfer_bits(9, TMS=bitarray('001011111'))
    assert d0.tapstate == "SHIFTDR"

    #READ 32 BITS OF DATA
    res = c.transfer_bits(32, TMS=ConstantBitarray(False, 32), TDO=True)
    print("RES IS", res, "(%s)"%type(res))
    assert d0.tapstate == "SHIFTDR"
    assert res == d0._idcode

def test_transfer_bits_adv():
    d0 = MockPhysicalJTAGDevice(name="D0", status=bitarray('11111100'),
                    idcode=bitarray('00000110110101001000000010010011'))
    ctrl = FakeXPCU1Handle(d0)
    c = getDriverInstanceForDevice(FakeUSBDev(ctrl))
    c.jtag_enable()

    #RESET, TRANS TO SHIFTDR, DO NOTHING, READ 32 BITS
    bits = c.transfer_bits(32+9, TMS=bitarray('0'*32 + '001011111'),
                           TDI=False,
                           TDO=ConstantBitarray(True, 32)+
                           ConstantBitarray(False, 9)
)
    assert d0.tapstate == "SHIFTDR"
    assert bits == d0._idcode
