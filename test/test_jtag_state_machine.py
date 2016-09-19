#-*- coding: utf-8 -*-
import pytest
from bitarray import bitarray

from proteusisc.jtagStateMachine import JTAGStateMachine

def test_initialize_correct_defaults():
    sm = JTAGStateMachine()
    assert sm.state == "_PRE5"

    sm = JTAGStateMachine(state="TLR")
    assert sm.state == "TLR"

def test_set_state():
    sm = JTAGStateMachine()
    sm.state = "RTI"
    assert sm.state == "RTI"

    with pytest.raises(ValueError):
        sm.state = "INVALID"

def test_transition_bit():
    """Assume the actual state list is correct because
    otherwise we have a lot of transitions to test."""
    sm = JTAGStateMachine()
    sm.state = "CAPTUREDR"
    sm.transition_bit(True)
    assert sm.state == "EXIT1DR"
    sm.transition_bit(True)
    assert sm.state == "UPDATEDR"

    sm.state = "CAPTUREDR"
    sm.transition_bit(False)
    assert sm.state == "SHIFTDR"
    sm.transition_bit(False)
    assert sm.state == "SHIFTDR"
    sm.transition_bit(True)
    assert sm.state == "EXIT1DR"

def test_calc_transition_to_state_changes_nothing():
    sm = JTAGStateMachine()
    assert sm.state == "_PRE5"
    sm.calc_transition_to_state("SHIFTDR")
    assert sm.state == "_PRE5"

def test_invalid_calc_transition_to_state():
    sm = JTAGStateMachine()

    def do_bits(bits):
        for bit in bits[::-1]:
            sm.transition_bit(bit)

    with pytest.raises(ValueError):
        sm.calc_transition_to_state("INV")

    #Test a path to _PRE5 is calculatable under initial conditions
    sm.state = "_PRE3"
    path = sm.calc_transition_to_state("_PRE5")
    assert path == bitarray('0')
    do_bits(path)
    assert sm.state == "_PRE5"

    sm.state = "SHIFTDR"
    with pytest.raises(ValueError):
        sm.calc_transition_to_state("_PRE5")

def test_calc_transition_to_state():
    sm = JTAGStateMachine()

    def do_bits(bits):
        for bit in bits[::-1]:
            sm.transition_bit(bit)

    path = sm.calc_transition_to_state("RTI")
    assert path == bitarray('011111')
    do_bits(path)
    assert sm.state, "RTI"

    path = sm.calc_transition_to_state("RTI")
    assert path == bitarray()
    do_bits(path)
    assert sm.state, "RTI"

    path = sm.calc_transition_to_state("TLR")
    assert path == bitarray('111')
    do_bits(path)
    assert sm.state, "TLR"

    path = sm.calc_transition_to_state("SHIFTDR")
    assert path == bitarray('0010')
    do_bits(path)
    assert sm.state, "SHIFTDR"

    path = sm.calc_transition_to_state("SHIFTIR")
    assert path == bitarray('001111')
    do_bits(path)
    assert sm.state, "SHIFTIR"
