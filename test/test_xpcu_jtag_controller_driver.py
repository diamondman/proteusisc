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
