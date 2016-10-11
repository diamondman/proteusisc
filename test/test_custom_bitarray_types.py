#-*- coding: utf-8 -*-
import pytest

from proteusisc.bittypes import CompositeBitarray, ConstantBitarray,\
    NoCareBitarray, bitarray, PreferFalseBitarray

def test_nocare():
    bits = NoCareBitarray(7)
    assert len(list(bits)) == 7
    assert not bits.all()
    assert not bits.any()
    assert bool(bits[0]) == False
    assert bool(bits[-1]) == False
    assert bool(bits[-7]) == False
    assert bool(bits[6]) == False
    with pytest.raises(IndexError):
        bits[7]
    with pytest.raises(IndexError):
        bits[-8]

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

    assert bits[0] == False
    assert bits[-1] == False
    assert bits[-3] == False
    assert bits[2] == False
    with pytest.raises(IndexError):
        bits[3]
    with pytest.raises(IndexError):
        bits[-4]

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
    assert bitarray(bits) == bitarray('111100000')

    bits = bits2 + bits1
    assert len(bits) == 9
    assert bitarray(bits) == bitarray('000001111')

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
    assert bitarray(bits) == bitarray('100100000')

    bits = bits2 + bits1
    assert len(bits) == 9
    assert bitarray(bits) == bitarray('000001001')

def test_constant_bitarray_add():
    #FOR TRUE
    bits1 = bitarray('1001')
    bits2 = ConstantBitarray(True, 5)
    bits = bits1 + bits2
    assert len(list(bits)) == 9
    assert bitarray(bits) == bitarray('100111111')

    bits = bits2 + bits1
    assert len(bits) == 9
    assert bitarray(bits) == bitarray('111111001')

    #FOR FALSE
    bits1 = bitarray('1001')
    bits2 = ConstantBitarray(False, 5)
    bits = bits1 + bits2
    assert len(bits) == 9
    assert bitarray(bits) == bitarray('100100000')

    bits = bits2 + bits1
    assert len(bits) == 9
    assert bitarray(bits) == bitarray('000001001')

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

    assert ConstantBitarray(False, 4) != 'INVALID'

#COMPOSITE BIT ARRAY
def test_composite_general():
    c1 = ConstantBitarray(True, 4)
    c2 = NoCareBitarray(5)
    comp = CompositeBitarray(c1, c2)
    assert len(comp) == 9
    assert comp.__repr__() == "<CMP: TTTT????? (9)>"

    c3 = bitarray('1001')
    comp2 = CompositeBitarray(comp, c3)
    assert len(comp2) == 13
    assert comp2.__repr__() == "<CMP: TTTT?????1001 (13)>"

    #NOT TESTING __getitem__ much BECAUSE NOT USED
    #Does not respect nocare combining with prims...
    assert comp2 == bitarray('1111000001001')
    #for i, bit in enumerate(bitarray('1111000001001')):
    #    assert comp2[i] == bit

    #TODO Add new index error check
    with pytest.raises(TypeError):
        comp2[99]

    with pytest.raises(TypeError):
        comp2['INVALID']

    assert comp2.prepare() == bitarray('1111111111001')
    comp2 = CompositeBitarray(comp, c3)
    assert bitarray(comp2.prepare()) == bitarray('1111111111001')
    comp2 = CompositeBitarray(comp, c3)
    assert comp2.prepare(preserve_history=True) == \
        bitarray('1111111111001')

def test_composite_general_preferfalse():
    c1 = ConstantBitarray(True, 4)
    c2 = PreferFalseBitarray(5)
    c3 = bitarray('1001')
    comp = c1 + c2 + c3
    assert isinstance(comp, CompositeBitarray)
    assert len(comp) == 13
    assert comp.__repr__() == "<CMP: TTTT?????1001 (13)>"

    assert comp.prepare() == bitarray('1111111111001')
    assert comp.prepare(preserve_history=True) == \
        bitarray('1111000001001')

def test_composite_invalid_add():
    c1 = NoCareBitarray(7)
    comp = CompositeBitarray(c1)
    with pytest.raises(TypeError):
        comp + 'invalid'
    with pytest.raises(TypeError):
        'invalid' + comp

def test_composite_composite_add():
    c1 = NoCareBitarray(7)
    comp = CompositeBitarray(c1)

    c2 = ConstantBitarray(True, 4)
    comp2 = CompositeBitarray(c2)

    comp3 = comp + comp2
    assert comp3.prepare() == bitarray('11111111111')
    #PRESERVE
    c1 = PreferFalseBitarray(7)
    comp = CompositeBitarray(c1)

    c2 = ConstantBitarray(True, 4)
    comp2 = CompositeBitarray(c2)

    comp3 = comp + comp2
    assert comp3.prepare(preserve_history=True) == bitarray('00000001111')

def test_composite_any_all_count():
    c1 = NoCareBitarray(7)
    c2 = ConstantBitarray(True, 3)
    comp = CompositeBitarray(c1, c2)
    assert comp.any()
    assert not comp.all() #Maybe this will change later.

    c1 = bitarray('111')
    c2 = ConstantBitarray(True, 3)
    comp = CompositeBitarray(c1, c2)
    assert comp.any()
    assert comp.all()

    c1 = NoCareBitarray(7)
    c2 = ConstantBitarray(False, 3)
    comp = CompositeBitarray(c1, c2)
    assert not comp.all()
    assert not comp.any()

def test_composite_count():
    c1 = NoCareBitarray(7)
    c2 = ConstantBitarray(True, 3)
    comp = CompositeBitarray(c1, c2)
    assert comp.count(False) == c1.count(False)+c2.count(False)
    assert comp.count(True) == c1.count(True)+c2.count(True)

    c1 = bitarray('111')
    c2 = ConstantBitarray(True, 3)
    comp = CompositeBitarray(c1, c2)
    assert comp.count(False) == c1.count(False)+c2.count(False)
    assert comp.count(True) == c1.count(True)+c2.count(True)

    c1 = NoCareBitarray(7)
    c2 = ConstantBitarray(False, 3)
    comp = CompositeBitarray(c1, c2)
    assert comp.count(False) == c1.count(False)+c2.count(False)
    assert comp.count(True) == c1.count(True)+c2.count(True)
