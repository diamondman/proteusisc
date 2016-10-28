#-*- coding: utf-8 -*-
import struct
import pytest

from proteusisc.controllerManager import getDriverInstanceForDevice
from proteusisc.jtagScanChain import JTAGScanChain
from proteusisc.test_utils import FakeUSBDev, FakeDevHandle,\
    MockPhysicalJTAGDevice, FakeXPCU1Handle
from proteusisc.bittypes import bitarray, NoCareBitarray

def test_black_hole_register_constraints_three_black_holes():
    #Tests that the compiler can work around black hole registers
    #to get data where it needs to go. The expected behavior is
    #to create three different frames, one per prim, but the frame
    #state is not being tested here... just the results in the regs.
    dev0 = MockPhysicalJTAGDevice(idcode=XC3S1200E_ID,
            name="D0", status=bitarray('111100'))
    dev1 = MockPhysicalJTAGDevice(idcode=XC3S1200E_ID,
            name="D1", status=bitarray('111101'))
    dev2 = MockPhysicalJTAGDevice(idcode=XC3S1200E_ID,
            name="D2", status=bitarray('111110'))
    usbdev = FakeUSBDev(FakeXPCU1Handle(dev0, dev1, dev2))
    chain = JTAGScanChain(getDriverInstanceForDevice(usbdev))
    d0, d1, d2 = get_XC3S1200E(chain), get_XC3S1200E(chain), \
                 get_XC3S1200E(chain)
    chain._hasinit = True
    chain._devices = [d0, d1, d2]

    chain.jtag_enable()

    d0.run_instruction("CFG_IN", data=bitarray('11010001'))
    d1.run_instruction("CFG_IN", data=bitarray('01101010111'))
    d2.run_instruction("CFG_IN",data=bitarray('11110'))

    chain.flush()
    assert "110100010110101011111110" not in dev0.\
        event_history, "All data written into the first black "\
        "hole register. Black Holes not avoided."
    #The extra zero in the arary are from shifting in the first
    #bits. Some of these zeros may go away if unnecessary trailing
    #bypass data is later skipped.
    assert "11010001" in dev0.DRs[None].dumpData().to01()
    assert "01101010111" in dev1.DRs[None].dumpData().to01()
    assert "11110" in dev2.DRs[None].dumpData().to01()

def test_black_hole_register_constraints_complimentary_prims():
    #Tests if a Blask Hole Read, a Black Hole Write, and a nocare
    #write are combined in a way that satisfies all requests.  The
    #expected behavior is to combine these three non colliding prims
    #into a single frame, but the frame state is not being tested
    #here... just the results in the regs.
    dev0 = MockPhysicalJTAGDevice(idcode=XC3S1200E_ID,
            name="D0", status=bitarray('111100'))
    dev1 = MockPhysicalJTAGDevice(idcode=XC3S1200E_ID,
            name="D1", status=bitarray('111101'))
    dev2 = MockPhysicalJTAGDevice(idcode=XC3S1200E_ID,
            name="D2", status=bitarray('111110'))
    usbdev = FakeUSBDev(FakeXPCU1Handle(dev0, dev1, dev2))
    chain = JTAGScanChain(getDriverInstanceForDevice(usbdev))
    d0, d1, d2 = get_XC3S1200E(chain), get_XC3S1200E(chain), \
                 get_XC3S1200E(chain)
    chain._hasinit = True
    chain._devices = [d0, d1, d2]

    chain.jtag_enable()

    d0.run_instruction("CFG_IN", data=bitarray('11010001'))
    d1.run_instruction("BYPASS", data=NoCareBitarray(1))
    a, _ = d2.run_instruction("CFG_IN", read=True, bitcount=8)

    chain.flush()
    assert a() == bitarray('00000000')
    assert "1101000100" in dev0.DRs[None].dumpData().to01()

XC3S1200E_ID = bitarray('00000001110000101110000010010011')
def get_XC3S1200E(chain):
    return chain.initialize_device_from_id(chain, XC3S1200E_ID)

def test_black_hole_register_constraints_bad_order_complimentary_prims():
    #Tests if a Blask Hole Read, a Black Hole Write, and a nocare
    #write are combined in a way that satisfies all requests.  The
    #expected behavior is to combine these three non colliding prims
    #into a single frame, but the frame state is not being tested
    #here... just the results in the regs.
    dev0 = MockPhysicalJTAGDevice(idcode=XC3S1200E_ID,
            name="D0", status=bitarray('111100'))
    dev1 = MockPhysicalJTAGDevice(idcode=XC3S1200E_ID,
            name="D1", status=bitarray('111101'))
    dev2 = MockPhysicalJTAGDevice(idcode=XC3S1200E_ID,
            name="D2", status=bitarray('111110'))
    usbdev = FakeUSBDev(FakeXPCU1Handle(dev0, dev1, dev2))
    chain = JTAGScanChain(getDriverInstanceForDevice(usbdev))
    d0, d1, d2 = get_XC3S1200E(chain), get_XC3S1200E(chain), \
                 get_XC3S1200E(chain)
    chain._hasinit = True
    chain._devices = [d0, d1, d2]

    chain.jtag_enable()

    d2.run_instruction("CFG_IN", data=bitarray('11010001'))
    d1.run_instruction("BYPASS", data=NoCareBitarray(1))
    a, _ = d1.run_instruction("CFG_IN", read=True, bitcount=8)

    chain.flush()
    assert a() == bitarray('00000000')
    assert "1101000100" in dev2.DRs[None].dumpData().to01()
