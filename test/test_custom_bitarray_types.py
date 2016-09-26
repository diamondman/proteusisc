#-*- coding: utf-8 -*-
import pytest
from bitarray import bitarray

from proteusisc.primitive import ConstantBitarray, NoCareBitarray

def test_nocare():
    bits = NoCareBitarray(7)
    assert len(list(bits)) == 7
    assert not bits.all()
    assert not bits.any()

def test_nocare_nocare_add():
    bits1 = NoCareBitarray(4)
    bits2 = NoCareBitarray(5)
    bits = bits1 + bits2
    assert isinstance(bits, NoCareBitarray)
    assert len(bits) == 9

    bits = bits2 + bits1
    assert isinstance(bits, NoCareBitarray)
    assert len(bits) == 9,\
        "Combining doesn't work in reerse"

def test_constant():
    bits = ConstantBitarray(True, 9)
    assert bits.all()
    assert bits.any()
    arr = list(bits)
    assert len(arr) == 9
    assert all(arr)

    bits = ConstantBitarray(False, 3)
    assert not bits.all()
    assert not bits.any()
    arr = list(bits)
    assert len(arr) == 3
    assert not any(arr)

def test_constant_constant_add():
    #FOR TRUE
    bits1 = ConstantBitarray(False, 4)
    bits2 = ConstantBitarray(False, 5)
    bits = bits1 + bits2
    assert isinstance(bits, ConstantBitarray)
    assert len(list(bits)) == 9
    assert not any(list(bits))

    bits = bits2 + bits1
    assert isinstance(bits, ConstantBitarray)
    assert len(bits) == 9
    assert not any(list(bits))

    #FOR FALSE
    bits1 = ConstantBitarray(True, 4)
    bits2 = ConstantBitarray(True, 5)
    bits = bits1 + bits2
    assert isinstance(bits, ConstantBitarray)
    assert len(list(bits)) == 9
    assert all(list(bits))

    bits = bits2 + bits1
    assert isinstance(bits, ConstantBitarray)
    assert len(bits) == 9
    assert bits.all()

    #FOR TRUE AND FALSE
    bits1 = ConstantBitarray(True, 4)
    bits2 = ConstantBitarray(False, 5)
    bits = bits1 + bits2
    assert len(bits) == 9
    assert all(bits[:4])
    assert not any(bits[4:])

    bits = bits2 + bits1
    assert len(bits) == 9
    assert not any(bits[:5])
    assert all(bits[5:])

def test_constant_nocare_add():
    #FOR FALSE
    bits1 = ConstantBitarray(False, 4)
    bits2 = NoCareBitarray(5)
    bits = bits1 + bits2
    assert isinstance(bits, ConstantBitarray)
    assert len(list(bits)) == 9
    assert not bits.any()

    bits = bits2 + bits1
    assert isinstance(bits, ConstantBitarray)
    assert len(bits) == 9
    assert not bits.any()

    #FOR FALSE
    bits1 = ConstantBitarray(True, 4)
    bits2 = NoCareBitarray(5)
    bits = bits1 + bits2
    assert isinstance(bits, ConstantBitarray)
    assert len(list(bits)) == 9
    assert bits.all()

    bits = bits2 + bits1
    assert isinstance(bits, ConstantBitarray)
    assert len(bits) == 9
    assert bits.all()

def test_nocare_bitarray_add():
    bits1 = bitarray('1001')
    bits2 = NoCareBitarray(5)
    bits = bits1 + bits2
    assert len(list(bits)) == 9
    assert bits[:4] == bits1

    bits = bits2 + bits1
    assert len(bits) == 9
    assert bits[5:] == bits1

def test_constant_bitarray_add():
    #FOR TRUE
    bits1 = bitarray('1001')
    bits2 = ConstantBitarray(True, 5)
    bits = bits1 + bits2
    assert len(list(bits)) == 9
    assert bits[:4] == bits1
    assert all(bits[5:])

    bits = bits2 + bits1
    assert len(bits) == 9
    assert bits[5:] == bits1
    assert all(bits[:4])

    #FOR FALSE
    bits1 = bitarray('1001')
    bits2 = ConstantBitarray(False, 5)
    bits = bits1 + bits2
    assert len(bits) == 9
    assert bits[:4] == bits1
    assert not any(bits[5:])

    bits = bits2 + bits1
    assert len(bits) == 9
    assert bits[5:] == bits1
    assert not any(bits[:4])

def test_nocare_bool_add():
    #FOR TRUE
    bits1 = NoCareBitarray(5)
    bits2 = True
    bits = bits1 + bits2
    assert len(bits) == 6
    assert bits[-1]

    bits = bits2 + bits1
    assert len(bits) == 6
    assert bits[0]

    #FOR FALSE
    bits1 = NoCareBitarray(5)
    bits2 = False
    bits = bits1 + bits2
    assert len(bits) == 6
    assert not bits[-1]

    bits = bits2 + bits1
    assert len(bits) == 6
    assert not bits[0]

def test_constant_bool_add():
    #FOR TRUE
    bits1 = ConstantBitarray(True, 5)
    bits2 = True
    bits = bits1 + bits2
    assert len(bits) == 6
    assert isinstance(bits, ConstantBitarray)
    assert bits.all()

    bits = bits2 + bits1
    assert len(bits) == 6
    assert isinstance(bits, ConstantBitarray)
    assert bits.all()

    #FOR FALSE
    bits1 = ConstantBitarray(True, 5)
    bits2 = False
    bits = bits1 + bits2
    assert len(bits) == 6
    assert bits[-1] == bits2
    assert all(bits[:-1])

    bits = bits2 + bits1
    assert len(bits) == 6
    assert bits[0] == bits2
    assert all(bits[1:])

def test_nocare_slice():
    bits = NoCareBitarray(7)
    bit_slice = bits[1:-1]
    assert len(bit_slice) == 5

def test_constant_slice():
    bits = ConstantBitarray(True, 7)
    bit_slice = bits[1:-1]
    assert len(bit_slice) == 5
    assert bit_slice.all()

    bits = ConstantBitarray(False, 7)
    bit_slice = bits[1:-1]
    assert len(bit_slice) == 5
    assert not bit_slice.any()

    with pytest.raises(TypeError):
        bits.__getitem__('invalid')

def test_nocare_illegal_index():
    bits = NoCareBitarray(7)
    with pytest.raises(IndexError):
        bits[100]
    with pytest.raises(TypeError):
        bits['invalid']


def test_constant_illegal_index():
    bits = ConstantBitarray(True, 7)
    with pytest.raises(IndexError):
        bits[100]
    with pytest.raises(TypeError):
        bits['invalid']

def test_constant_invalid_add():
    bits = ConstantBitarray(True, 7)
    with pytest.raises(TypeError):
        bits + 'invalid'
    with pytest.raises(TypeError):
        'invalid' + bits

def test_nocare_invalid_add():
    bits = NoCareBitarray(7)
    with pytest.raises(TypeError):
        bits + 'invalid'
    with pytest.raises(TypeError):
        'invalid' + bits

def test_nocare_count():
    bits = NoCareBitarray(7)
    assert bits.count(val=False) == 0
    assert bits.count(val=True) == 0

def test_constant_count():
    bits = ConstantBitarray(True, 12)
    assert bits.count(val=False) == 0
    assert bits.count(val=True) == 12

    bits = ConstantBitarray(False, 12)
    assert bits.count(val=False) == 12
    assert bits.count(val=True) == 0

def test_constant_eq():
    assert ConstantBitarray(True, 7) == bitarray('1111111')
    assert ConstantBitarray(True, 7) != bitarray('111111')
    assert ConstantBitarray(True, 7) != bitarray('0000000')
    assert ConstantBitarray(False, 4) == bitarray('0000')
    assert ConstantBitarray(False, 4) != bitarray('000')
    assert ConstantBitarray(False, 4) != bitarray('1111')

    assert ConstantBitarray(False, 2) == ConstantBitarray(False, 2)
    assert ConstantBitarray(True, 2) == ConstantBitarray(True, 2)
    assert ConstantBitarray(False, 3) != ConstantBitarray(False, 2)
    assert ConstantBitarray(True, 2) != ConstantBitarray(False, 2)
