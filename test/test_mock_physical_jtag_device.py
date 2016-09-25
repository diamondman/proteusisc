#-*- coding: utf-8 -*-
import pytest
from bitarray import bitarray
from proteusisc.test_utils import MockPhysicalJTAGDevice

def test_initialize_correct_defaults():
    dev = MockPhysicalJTAGDevice(name="D0")
    assert dev.tapstate == "_PRE5"
    assert dev.name == "D0"

def test_shift():
    dev = MockPhysicalJTAGDevice(name="D0", status=bitarray('11111101'))
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

def test_idcode_ins_loads_id_code():
    dev = MockPhysicalJTAGDevice(name="D0", status=bitarray('11111101'))
    #MOVE TO SHIFTDR. Prepare to read idcode.
    for tms in reversed(bitarray('001011111')):
        dev.shift(tms, False)

    #READ OUT IDCODE TO CLEAR IT
    for tms in reversed(bitarray('10000000000000000000000000000000')):
        dev.shift(tms, False)

    #GO TO SHIFTIR
    for tms in reversed(bitarray('00111')):
        dev.shift(tms, False)
    assert dev.tapstate == "SHIFTIR"

    #SHIFT IN 'IDCODE' instruction (00000001)
    tmsbits = bitarray('10000000')[::-1]
    tdibits = bitarray('00000001')[::-1]
    for bit in range(len(tmsbits)):
        dev.shift(tmsbits[bit], tdibits[bit])

    #GO TO SHIFTDR
    for tms in reversed(bitarray('00101')):
        dev.shift(tms, False)

    #READIDCODE
    read_idcode = bitarray()
    real_idcode = dev.idcode
    for i in range(31):
        read_idcode.append(dev.shift(False, True))
    read_idcode.append(dev.shift(True, True))
    assert read_idcode[::-1] == real_idcode

def test_captureDR_loads_reg():
    #Not correctly simulating the device prevented detection of an issue
    #in the scan chain that caused initialization to loop forever,
    #constantly redetecting the same device. The fix was to check that
    #the IDCODE register is updated in the CaptureDR state.
    dev = MockPhysicalJTAGDevice(name="D0", status=bitarray('11111101'))

    #CHANGE TO SHIFTDR
    for tms in reversed(bitarray('001011111')):
        dev.shift(tms, False)

    #READ OUT IDCODE TO CLEAR IT
    for tms in reversed(bitarray('10000000000000000000000000000000')):
        dev.shift(tms, False)

    #LOOP BACK AROUND TO SHIFTDR THROUGH CAPTUREDR
    for tms in reversed(bitarray('0011')):
        dev.shift(tms, False)

    #READ OUT IDCODE TO CLEAR IT
    read_idcode = bitarray()
    real_idcode = dev.idcode
    for tms in reversed(bitarray('10000000000000000000000000000000')):
        read_idcode.append(dev.shift(tms, False))
    assert read_idcode[::-1] == real_idcode
