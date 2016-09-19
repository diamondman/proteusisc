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
