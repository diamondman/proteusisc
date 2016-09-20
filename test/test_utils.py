#-*- coding: utf-8 -*-
from bitarray import bitarray

from proteusisc.jtagUtils import bitfieldify, blen2Blen, buff2Blen,\
    build_byte_align_buff

from proteusisc.utils import memoized

def test_util_blen2Blen():
    assert blen2Blen(0) == 0
    assert blen2Blen(7) == 1
    assert blen2Blen(8) == 1
    assert blen2Blen(9) == 2

def test_util_buff2Blen():
    assert buff2Blen(bitarray(0)) == 0
    assert buff2Blen(bitarray(7)) == 1
    assert buff2Blen(bitarray(8)) == 1
    assert buff2Blen(bitarray(9)) == 2

def test_util_build_byte_align_buff():
    assert build_byte_align_buff(bitarray('1')) ==\
        bitarray('00000001')
    assert build_byte_align_buff(bitarray('1'*3)) ==\
        bitarray('00000111')
    assert build_byte_align_buff(bitarray('1'*8)) ==\
        bitarray('1'*8)
    assert build_byte_align_buff(bitarray('1'*9)) ==\
        bitarray('0000000111111111')

def test_util_bitfieldify():
    assert bitfieldify(b'\x01\xFF', 9) == bitarray('1'*9)

def test_util_memoized():
    def some_func(num):
        return num*num

    @memoized
    def some_memoized_func(num):
        return num*num

    for _ in range(2):
        for i in range(10):
            assert some_memoized_func(i) == some_func(i)

    #Check memoized does not fail with non hashable inputs
    @memoized
    def unit_function(data):
        return data
    assert unit_function([1,2,3]) == [1,2,3]
