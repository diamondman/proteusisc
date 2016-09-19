#-*- coding: utf-8 -*-
import pytest
from bitarray import bitarray

from proteusisc.contracts import Requirement,\
    NOCARE, ZERO, ONE, CONSTANT, CONSTANTZERO, CONSTANTONE, ARBITRARY

def test_requirement_is_nocare():
    assert NOCARE.isnocare
    assert not ZERO.isnocare
    assert not ONE.isnocare
    assert not CONSTANTZERO.isnocare
    assert not CONSTANTONE.isnocare
    assert not ARBITRARY.isnocare

    assert not NOCARE.isarbitrary
    assert not ZERO.isarbitrary
    assert not ONE.isarbitrary
    assert not CONSTANTZERO.isarbitrary
    assert not CONSTANTONE.isarbitrary
    assert ARBITRARY.isarbitrary

    assert not NOCARE.isconstant
    assert not ZERO.isconstant
    assert not ONE.isconstant
    assert CONSTANTZERO.isconstant
    assert CONSTANTONE.isconstant
    assert not ARBITRARY.isconstant

    assert not NOCARE.issingle
    assert ZERO.issingle
    assert ONE.issingle
    assert not CONSTANTZERO.issingle
    assert not CONSTANTONE.issingle
    assert not ARBITRARY.issingle

    r = Requirement(False, False, False, False)
    assert r.isnocare
    r = Requirement(False, False, False, True)
    assert r.isnocare

def test_requirement_satisfaction():
    capabilities = [NOCARE, ARBITRARY, CONSTANT, ZERO, ONE]
    result_mat = [
        [True, False, False, False, False],
        [True, True, True, True, True],
        [True, None, True, True, True],
        [True, None, None, True, False],
        [True, None, None, False, True],
    ]

    for cap_index, capability in enumerate(capabilities):
        for req_index, requirement in enumerate(capabilities):
            res = capability.satisfies(requirement)
            should_be = result_mat[cap_index][req_index]
            if should_be is None:
                should_be = False
            if not should_be == res:
                print(result_mat[cap_index])
                assert should_be == res,\
                "%s(%s) should %ssatisfy %s(%s)"%\
                (capability, cap_index, "" if should_be else "not ",
                 requirement, req_index)

def test_requirement_repr():
    caps_idents = [(NOCARE, '-'), (ARBITRARY, 'A'), (CONSTANT, 'C'),
                    (ZERO, 'F'), (ONE, 'T')]
    for cap, ident in caps_idents:
        assert cap.__repr__()[:1] == ident

def test_requirement_addition():
    #There are 256 combinations here that should all be tested.  The
    #boolean expression derived from the Kmap is pretty hard to break
    #without breaking the whole thing. For now, just some common ones
    #to make sure it works at all.

    with pytest.raises(TypeError):
        ONE + "INVALID"
    with pytest.raises(TypeError):
        "INVALID" + ONE

    res = ONE + ZERO
    assert res.arbitrary

    res = ONE + ONE
    assert res.issingle and res.value

    res = ZERO + ZERO
    assert res.issingle and not res.value

    res = ZERO + ARBITRARY
    assert res.isarbitrary
    res = ARBITRARY + ZERO
    assert res.isarbitrary

def test_requirement_copy():
    for cap in [NOCARE, ARBITRARY, CONSTANT, ZERO, ONE]:
        tmp = cap.copy()
        assert (tmp.A, tmp.B, tmp.C, tmp.D) == \
            (cap.A, cap.B, cap.C, cap.D)

def test_requirement_score():
    assert ONE.score > NOCARE.score
    assert ONE.score == ZERO.score
    assert CONSTANT.score > ZERO.score
    assert ARBITRARY.score > CONSTANT.score
