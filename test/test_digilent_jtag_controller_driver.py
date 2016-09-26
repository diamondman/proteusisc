#-*- coding: utf-8 -*-
import pytest
from bitarray import bitarray

from proteusisc.controllerManager import getDriverInstanceForDevice
from proteusisc.test_utils import FakeUSBDev, FakeDevHandle,\
    MockPhysicalJTAGDevice
from proteusisc.primitive import ConstantBitarray
from proteusisc.drivers.digilentdriver import DigilentWriteTMSPrimitive,\
    DigilentWriteTDIPrimitive, DigilentWriteTMSTDIPrimitive,\
    DigilentReadTDOPrimitive, DigilentClockTickPrimitive
from proteusisc.promise import TDOPromise

def test_jtag_onoff():
    ctrl = FakeDevHandle()
    c = getDriverInstanceForDevice(FakeUSBDev(ctrl))

    assert not ctrl.jtagon
    c.jtag_enable()
    assert ctrl.jtagon
    c.jtag_disable()
    assert not ctrl.jtagon

def test_write_tms_bits():
    d0 = MockPhysicalJTAGDevice(name="D0", status=bitarray('11111100'),
                    idcode=bitarray('00000110110101001000000010010011'))
    ctrl = FakeDevHandle(d0)
    c = getDriverInstanceForDevice(FakeUSBDev(ctrl))
    c.jtag_enable()

    #RESET TAP AND TRANS TO SHIFTDR
    c.write_tms_bits(bitarray('001011111'))
    assert d0.tapstate == "SHIFTDR"

    #READ 32 BITS OF DATA
    bits = c.write_tms_bits(ConstantBitarray(False, 32), return_tdo=True, TDI=False)
    assert d0.tapstate == "SHIFTDR"
    assert bits == d0._idcode

    #Read out the TDI value shifted in
    bits = c.write_tms_bits(ConstantBitarray(False, 32), return_tdo=True, TDI=True)
    assert d0.tapstate == "SHIFTDR"
    assert bits == ConstantBitarray(False, 32)

    #Read out the TDI value shifted in
    bits = c.write_tms_bits(ConstantBitarray(False, 32), return_tdo=True)
    assert d0.tapstate == "SHIFTDR"
    assert bits == ConstantBitarray(True, 32)

def test_write_tdi_bits():
    d0 = MockPhysicalJTAGDevice(name="D0", status=bitarray('11111100'),
                    idcode=bitarray('00000110110101001000000010010011'))
    ctrl = FakeDevHandle(d0)
    c = getDriverInstanceForDevice(FakeUSBDev(ctrl))
    c.jtag_enable()

    #RESET TAP AND TRANS TO SHIFTDR
    for bit in reversed(bitarray('001011111')):
        c.write_tdi_bits(bitarray('0'), TMS=bit)
    assert d0.tapstate == "SHIFTDR"

    #READ 32 BITS OF DATA
    bits = c.write_tdi_bits(ConstantBitarray(False, 32), return_tdo=True, TMS=False)
    assert d0.tapstate == "SHIFTDR"
    assert bits == d0._idcode

    #Read out the TDI value shifted in
    bits = c.write_tdi_bits(ConstantBitarray(True, 32), return_tdo=True, TMS=False)
    assert d0.tapstate == "SHIFTDR"
    assert bits == ConstantBitarray(False, 32)

    #Read out the TDI value shifted in
    bits = c.write_tdi_bits(ConstantBitarray(False, 32), return_tdo=True)
    assert d0.tapstate == "SHIFTDR"
    assert bits == ConstantBitarray(True, 32)

def test_write_tms_tdi_bits():
    d0 = MockPhysicalJTAGDevice(name="D0", status=bitarray('11111100'),
                    idcode=bitarray('00000110110101001000000010010011'))
    ctrl = FakeDevHandle(d0)
    c = getDriverInstanceForDevice(FakeUSBDev(ctrl))
    c.jtag_enable()

    #RESET TAP AND TRANS TO SHIFTDR
    c.write_tms_tdi_bits(bitarray('001011111'), ConstantBitarray(False, 9))
    assert d0.tapstate == "SHIFTDR"

    #READ 32 BITS OF DATA
    next_read_bits = bitarray('11001010001101011100101000110101')
    bits = c.write_tms_tdi_bits(ConstantBitarray(False, 32), next_read_bits,
                                return_tdo=True)
    assert d0.tapstate == "SHIFTDR"
    assert bits == d0._idcode

    #Read out the TDI value shifted in
    bits = c.write_tms_tdi_bits(ConstantBitarray(False, 32),
                                ConstantBitarray(False, 32), return_tdo=True)
    assert d0.tapstate == "SHIFTDR"
    assert bits == next_read_bits

def test_read_tdo_bits():
    d0 = MockPhysicalJTAGDevice(name="D0", status=bitarray('11111100'),
                    idcode=bitarray('00000110110101001000000010010011'))
    ctrl = FakeDevHandle(d0)
    c = getDriverInstanceForDevice(FakeUSBDev(ctrl))
    c.jtag_enable()

    #RESET TAP AND TRANS TO SHIFTDR
    for bit in reversed(bitarray('001011111')):
        c.read_tdo_bits(1, TMS=bit, TDI=False)
    assert d0.tapstate == "SHIFTDR"

    #READ 32 BITS OF DATA
    bits = c.read_tdo_bits(32, TMS=False, TDI=False)
    assert d0.tapstate == "SHIFTDR"
    assert bits == d0._idcode

    #Read out the TDI value shifted in
    bits = c.read_tdo_bits(32, TMS=False, TDI=True)
    assert d0.tapstate == "SHIFTDR"
    assert bits == ConstantBitarray(False, 32)

    #Read out the TDI value shifted in
    bits = c.read_tdo_bits(32, TMS=False)
    assert d0.tapstate == "SHIFTDR"
    assert bits == ConstantBitarray(True, 32)

def test_tick_clock():
    d0 = MockPhysicalJTAGDevice(name="D0", status=bitarray('11111100'),
                    idcode=bitarray('00000110110101001000000010010011'))
    ctrl = FakeDevHandle(d0)
    c = getDriverInstanceForDevice(FakeUSBDev(ctrl))
    c.jtag_enable()

    #RESET TAP AND TRANS TO SHIFTDR
    for bit in reversed(bitarray('001011111')):
        c.tick_clock(1, TMS=bit, TDI=False)
    assert d0.tapstate == "SHIFTDR"

    #Write 32 bits of data
    bits = c.tick_clock(32, TMS=False, TDI=False)
    assert d0.tapstate == "SHIFTDR"

    #Read out the TDI value shifted in
    bits = c.read_tdo_bits(32, TMS=False)
    assert d0.tapstate == "SHIFTDR"
    assert bits == ConstantBitarray(False, 32)

    #WRITE A DIFFERENT VALUE
    c.tick_clock(32, TMS=False, TDI=True)

    #Read out the TDI value shifted in
    bits = c.read_tdo_bits(32, TMS=False)
    assert d0.tapstate == "SHIFTDR"
    assert bits == ConstantBitarray(True, 32)



def test_write_tms_bits_primitive():
    d0 = MockPhysicalJTAGDevice(name="D0", status=bitarray('11111100'),
                    idcode=bitarray('00000110110101001000000010010011'))
    ctrl = FakeDevHandle(d0)
    c = getDriverInstanceForDevice(FakeUSBDev(ctrl))
    c.jtag_enable()

    #RESET TAP AND TRANS TO SHIFTDR
    prim = DigilentWriteTMSPrimitive(tms=bitarray('001011111'),
                                     reqef=(), _chain=None)
    c.execute([prim])
    assert d0.tapstate == "SHIFTDR"

    #READ 32 BITS OF DATA
    promise = TDOPromise(None, 0, 32)
    prim = DigilentWriteTMSPrimitive(tms=ConstantBitarray(False,32),
                                     tdo=ConstantBitarray(True,32),
                                     _chain=None, _promise=promise,
                                     reqef=())
    c.execute([prim])
    assert d0.tapstate == "SHIFTDR"
    assert promise() == d0._idcode

def test_write_tdi_bits_primitive():
    d0 = MockPhysicalJTAGDevice(name="D0", status=bitarray('11111100'),
                    idcode=bitarray('00000110110101001000000010010011'))
    ctrl = FakeDevHandle(d0)
    c = getDriverInstanceForDevice(FakeUSBDev(ctrl))
    c.jtag_enable()

    #RESET TAP AND TRANS TO SHIFTDR
    for bit in reversed(bitarray('001011111')):
        prim = DigilentWriteTDIPrimitive(
            tdi=ConstantBitarray(False, 1),
            tms=ConstantBitarray(bit, 1),
            reqef=(), _chain=None
        )
        c.execute([prim])
    assert d0.tapstate == "SHIFTDR"

    #READ 32 BITS OF DATA
    promise = TDOPromise(None, 0, 32)
    prim = DigilentWriteTDIPrimitive(
        tms=ConstantBitarray(False,32),
        tdi=ConstantBitarray(False,32),
        tdo=ConstantBitarray(True,32),
        _chain=None, _promise=promise,
        reqef=()
    )
    c.execute([prim])
    assert d0.tapstate == "SHIFTDR"
    assert promise() == d0._idcode

def test_write_tms_tdi_bits_primitive():
    d0 = MockPhysicalJTAGDevice(name="D0", status=bitarray('11111100'),
                    idcode=bitarray('00000110110101001000000010010011'))
    ctrl = FakeDevHandle(d0)
    c = getDriverInstanceForDevice(FakeUSBDev(ctrl))
    c.jtag_enable()

    #RESET TAP AND TRANS TO SHIFTDR
    prim = DigilentWriteTMSTDIPrimitive(
        tms=bitarray('001011111'),
        tdi=ConstantBitarray(False, 9),
        reqef=(), _chain=None
    )
    c.execute([prim])
    assert d0.tapstate == "SHIFTDR"

    #READ 32 BITS OF DATA
    promise = TDOPromise(None, 0, 32)
    prim = DigilentWriteTMSTDIPrimitive(
        tdi=ConstantBitarray(False,32),
        tms=ConstantBitarray(False,32),
        tdo=ConstantBitarray(True,32),
        _chain=None, _promise=promise,
        reqef=())
    c.execute([prim])
    assert d0.tapstate == "SHIFTDR"
    assert promise() == d0._idcode

def test_read_tdo_primitie():
    d0 = MockPhysicalJTAGDevice(name="D0", status=bitarray('11111100'),
                    idcode=bitarray('00000110110101001000000010010011'))
    ctrl = FakeDevHandle(d0)
    c = getDriverInstanceForDevice(FakeUSBDev(ctrl))
    c.jtag_enable()

    #RESET TAP AND TRANS TO SHIFTDR
    for bit in reversed(bitarray('001011111')):
        prim = DigilentReadTDOPrimitive(
            tdi=False, tms=bit,
            reqef=(), _chain=None
        )
        c.execute([prim])
    assert d0.tapstate == "SHIFTDR"

    #READ 32 BITS OF DATA
    promise = TDOPromise(None, 0, 32)
    prim = DigilentReadTDOPrimitive(
        count=32, tdi=False, tms=False,
        _chain=None, _promise=promise,
        reqef=())
    c.execute([prim])
    assert d0.tapstate == "SHIFTDR"
    assert promise() == d0._idcode

def test_clock_tick_primitive():
    d0 = MockPhysicalJTAGDevice(name="D0", status=bitarray('11111100'),
                    idcode=bitarray('00000110110101001000000010010011'))
    ctrl = FakeDevHandle(d0)
    c = getDriverInstanceForDevice(FakeUSBDev(ctrl))
    c.jtag_enable()

    #RESET TAP AND TRANS TO SHIFTDR
    for bit in reversed(bitarray('001011111')):
        prim = DigilentClockTickPrimitive(
            tdi=False, tms=bit,
            reqef=(), _chain=None
        )
        c.execute([prim])
    assert d0.tapstate == "SHIFTDR"
