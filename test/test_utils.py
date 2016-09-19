#-*- coding: utf-8 -*-
from bitarray import bitarray

from proteusisc.jtagUtils import bitfieldify, blen2Blen, buff2Blen,\
    build_byte_align_buff

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
