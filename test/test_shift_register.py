#-*- coding: utf-8 -*-
import pytest
from bitarray import bitarray

from proteusisc.test_utils import ShiftRegister

def test_initialization():
    reg = ShiftRegister(8)
    assert reg.size == 8, "Size not set correctly"
    assert len(reg.dumpData()) == 8, "Data not correct length"

    reg = ShiftRegister(17)
    assert reg.size == 17, "Size not set correctly"
    assert len(reg.dumpData()) == 17, "Data not correct length"

    reg = ShiftRegister(8, initval=False)
    assert reg.dumpData() == bitarray('00000000'),\
        "data not initialized to 0"

    reg = ShiftRegister(8, initval=True)
    assert reg.dumpData() == bitarray('11111111'),\
        "data not initialized to 1"

    initval = bitarray('11001010')
    reg = ShiftRegister(8, initval=initval)
    assert reg.dumpData() == initval,\
        "data not initialized to 11001010"

    with pytest.raises(ValueError):
        toobiginitval = bitarray('1100101011110000')
        ShiftRegister(8, initval=toobiginitval)

def test_clear():
    reg = ShiftRegister(8, initval=True)
    reg.clear()
    assert reg.size == 8, "Size cleared!"
    assert reg.dumpData() == bitarray('00000000'),\
        "Data not cleared"

def test_shift():
    initval = bitarray('11001010')

    reg = ShiftRegister(8, initval=initval)
    for i in reversed(initval):
        assert i == reg.shift(False), "Wrong value shifted out"
    assert reg.dumpData() == bitarray('0'*8),\
        "Data not shifted in correctly"

    reg = ShiftRegister(8, initval=initval)
    for i in reversed(initval):
        assert i == reg.shift(True), "Wrong value shifted out"
    assert reg.dumpData() == bitarray('1'*8),\
        "Data not shifted in correctly"
