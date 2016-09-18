#-*- coding: utf-8 -*-
import pytest
from bitarray import bitarray
from proteusisc.test_utils import MockPhysicalJTAGDevice

def test_initialize_correct_defaults():
    dev = MockPhysicalJTAGDevice(name="D0")
    assert dev.tapstate == "_PRE5"
    assert dev.name == "D0"

def test_shift():
    dev = MockPhysicalJTAGDevice(name="D0")
    #MOVE TO SHIFTDR. Prepare to read idcode.
    for tms in reversed(bitarray('001011111')):
        dev.shift(tms, False)
    assert dev.tapstate == "SHIFTDR",\
        "Device TAP did not respond correctly to tms bits"
    assert "RESET" in dev.event_history
    assert "RTI" in dev.event_history
    assert "CAPTUREDR" in dev.event_history

    #Test reading IDcode works
    dev.clearhistory()
    read_idcode = bitarray()
    real_idcode = dev.idcode
    for i in range(31):
        read_idcode.append(dev.shift(False, True))
    read_idcode.append(dev.shift(True, True))
    assert read_idcode[::-1] == real_idcode
    assert "UPDATEDR" not in dev.event_history
    #UPDATE THE REGISTER
    read_idcode.append(dev.shift(True, True))
    assert "UPDATEDR" in dev.event_history

    #Test setting an IR
    dev.clearhistory()
    read_status = bitarray()
    for tms in reversed(bitarray('0011')):
        dev.shift(tms, False)
    assert dev.tapstate == "SHIFTIR",\
        "Device TAP did not respond correctly to tms bits"
    real_status = dev.calc_status_register().dumpData()
    for i in range(dev.irlen-1):
        read_status.append(dev.shift(False, True))
    read_status.append(dev.shift(True, True))
    assert read_status[::-1] == real_status
    assert "UPDATEIR" not in dev.event_history
    read_idcode.append(dev.shift(True, True))
    assert "UPDATEIR" in dev.event_history
