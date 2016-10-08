#-*- coding: utf-8 -*-
import struct
import pytest

from proteusisc.controllerManager import getDriverInstanceForDevice
from proteusisc.jtagScanChain import JTAGScanChain
from proteusisc.test_utils import FakeUSBDev, FakeDevHandle,\
    MockPhysicalJTAGDevice
from proteusisc.primitive import ConstantBitarray, Bitarray

def test_init_chain_single():
    idcode = Bitarray('00000110110101001000000010010011')
    ctrl = FakeDevHandle(
        MockPhysicalJTAGDevice(name="D0", idcode=idcode),
    )
    usbdev = FakeUSBDev(ctrl)
    c = getDriverInstanceForDevice(usbdev)
    chain = JTAGScanChain(c)
    chain.init_chain()

    assert len(chain._devices) == 1
    devid = struct.unpack("<L", idcode.tobytes()[::-1])[0]
    assert chain._devices[0]._id == devid

def test_init_chain_triple():
    codes = (
        Bitarray('00000110110101001000000010010011'),
        Bitarray('01000110110101001000000010010011'),
        Bitarray('10000110110101001000000010010011')
        )
    ctrl = FakeDevHandle(
        MockPhysicalJTAGDevice(name="D0", idcode=codes[0]),
        MockPhysicalJTAGDevice(name="D1", idcode=codes[1]),
        MockPhysicalJTAGDevice(name="D2", idcode=codes[2]),
    )
    usbdev = FakeUSBDev(ctrl)
    c = getDriverInstanceForDevice(usbdev)
    chain = JTAGScanChain(c)
    chain.init_chain()

    assert len(chain._devices) == 3
    for i, dev in enumerate(chain._devices):
        devid = struct.unpack("<L", codes[i].tobytes()[::-1])[0]
        assert dev._id == devid

def test_set_desired_speed():
    ctrl = FakeDevHandle()
    usbdev = FakeUSBDev(ctrl)
    c = getDriverInstanceForDevice(usbdev)
    chain = JTAGScanChain(c)

    assert c.speed == None
    chain.jtag_enable()
    assert c.speed == 4000000
    chain.jtag_disable()

    chain.speed = 1000000
    chain.jtag_enable()
    assert c.speed == 1000000

def test_read_ir_1(chain_1dev):
    a = chain_1dev.rw_ir(bitcount=8, read=True)
    assert a() == Bitarray('11111100')

#READ IR 3 device TESTS
def test_read_ir_3_100(chain_3dev):
    c = chain_3dev.rw_ir(bitcount=8, read=False, lastbit=False)
    b = chain_3dev.rw_ir(bitcount=8, read=False, lastbit=False)
    a = chain_3dev.rw_ir(bitcount=8, read=True)
    assert a() == Bitarray('11111100')
    assert not b
    assert not c

def test_read_ir_3_001(chain_3dev):
    c = chain_3dev.rw_ir(bitcount=8, read=True, lastbit=False)
    b = chain_3dev.rw_ir(bitcount=8, read=False, lastbit=False)
    a = chain_3dev.rw_ir(bitcount=8, read=False)
    assert not a
    assert not b
    assert c() == Bitarray('11111110')

def test_read_ir_3_100(chain_3dev):
    c = chain_3dev.rw_ir(bitcount=8, read=True, lastbit=False)
    b = chain_3dev.rw_ir(bitcount=8, read=False, lastbit=False)
    a = chain_3dev.rw_ir(bitcount=8, read=True)
    assert a() == Bitarray('11111100')
    assert not b
    assert c() == Bitarray('11111110')

def test_read_ir_3_111(chain_3dev):
    c = chain_3dev.rw_ir(bitcount=8, read=True, lastbit=False)
    b = chain_3dev.rw_ir(bitcount=8, read=True, lastbit=False)
    a = chain_3dev.rw_ir(bitcount=8, read=True)

    #a = d0.rw_dev_ir(bitcount=8, read=True)
    #b = d1.rw_dev_ir(bitcount=8, read=True)
    #c = d0.rw_dev_ir(bitcount=8, read=True)

    assert a() == Bitarray('11111100')
    assert b() == Bitarray('11111101')
    assert c() == Bitarray('11111110')

def test_read_dev_ir_3_111(chain_3dev):
    d0, d1, d2 = chain_3dev._devices
    a = d0.rw_dev_ir(bitcount=8, read=True)
    b = d1.rw_dev_ir(bitcount=8, read=True)
    c = d2.rw_dev_ir(bitcount=8, read=True)

    assert a() == Bitarray('11111100')
    assert b() == Bitarray('11111101')
    assert c() == Bitarray('11111110')

def test_read_dev_ir_multiple(chain_3dev):
    d0, d1, d2 = chain_3dev._devices
    a = d0.rw_dev_ir(bitcount=8, read=True)
    b = d1.rw_dev_ir(bitcount=8, read=True)
    c = d0.rw_dev_ir(bitcount=8, read=True)

    assert a() == Bitarray('11111100')
    assert b() == Bitarray('11111101')
    assert c() == Bitarray('11111100')

def test_read_dev_dr_multiple(chain_3dev):
    d0, d1, d2 = chain_3dev._devices
    a = d0.rw_dev_dr(regname="DEVICE_ID", read=True)
    b = d1.rw_dev_dr(regname="DEVICE_ID", read=True)
    c = d2.rw_dev_dr(regname="DEVICE_ID", read=True)

    assert a() == Bitarray('00000110110101001000000010010011')
    assert b() == Bitarray('01000110110101001000000010010011')
    assert c() == Bitarray('10000110110101001000000010010011')

def test_execute_single_instruction_on_1dev_chain(chain_1dev):
    d0, = chain_1dev._devices
    a, stat = d0.run_instruction("IDCODE", read=True)
    assert a() == Bitarray('00000110110101001000000010010011')
    assert stat is None

    a, stat = d0.run_instruction("IDCODE", read_status=True)
    assert a is None
    assert stat() == Bitarray('11111100')

    a, stat = d0.run_instruction("IDCODE", read=True, read_status=True)
    assert a() == Bitarray('00000110110101001000000010010011')
    assert stat() == Bitarray('11111100')

@pytest.fixture
def chain_1dev():
    ctrl = FakeDevHandle(
        MockPhysicalJTAGDevice(name="D0", status=Bitarray('11111100')),
    )
    usbdev = FakeUSBDev(ctrl)
    c = getDriverInstanceForDevice(usbdev)
    chain = JTAGScanChain(c)

    devid = Bitarray('11110110110101001100000010010011')
    d0 = chain.initialize_device_from_id(chain, devid)
    chain._hasinit = True
    chain._devices = [d0]

    chain.jtag_enable()
    return chain

@pytest.fixture
def chain_3dev():
    ctrl = FakeDevHandle(
        MockPhysicalJTAGDevice(name="D0", status=Bitarray('11111100'),
                    idcode=Bitarray('00000110110101001000000010010011')),
        MockPhysicalJTAGDevice(name="D1", status=Bitarray('11111101'),
                    idcode=Bitarray('01000110110101001000000010010011')),
        MockPhysicalJTAGDevice(name="D2", status=Bitarray('11111110'),
                    idcode=Bitarray('10000110110101001000000010010011'))
    )
    usbdev = FakeUSBDev(ctrl)
    c = getDriverInstanceForDevice(usbdev)
    chain = JTAGScanChain(c)

    devid = Bitarray('11110110110101001100000010010011')
    d0 = chain.initialize_device_from_id(chain, devid)
    d1 = chain.initialize_device_from_id(chain, devid)
    d2 = chain.initialize_device_from_id(chain, devid)
    chain._hasinit = True
    chain._devices = [d0, d1, d2]

    chain.jtag_enable()
    return chain
