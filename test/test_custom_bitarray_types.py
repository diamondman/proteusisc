#-*- coding: utf-8 -*-
import pytest

from proteusisc.bittypes import CompositeBitarray, ConstantBitarray,\
    NoCareBitarray, Bitarray

def test_nocare():
    bits = NoCareBitarray(7)
    assert len(list(bits)) == 7
    assert not bits.all()
    assert not bits.any()
    assert bits[0] == False
    assert bits[-1] == False
    assert bits[-7] == False
    assert bits[6] == False
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
    bits1 = Bitarray('1001')
    bits2 = NoCareBitarray(5)
    bits = bits1 + bits2
    assert len(list(bits)) == 9
    assert bits[:4] == bits1

    bits = bits2 + bits1
    assert len(bits) == 9
    assert bits[5:] == bits1

def test_constant_bitarray_add():
    #FOR TRUE
    bits1 = Bitarray('1001')
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
    bits1 = Bitarray('1001')
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

def test_nocarepreserve_bool_add():
    #FOR TRUE
    bits1 = NoCareBitarray(5, _preserve=True)
    bits2 = True
    bits = bits1 + bits2
    assert len(bits) == 6
    print(bits)
    assert bits[-1]

    bits = bits2 + bits1
    assert len(bits) == 6
    assert bits[0]

    #FOR FALSE
    bits1 = NoCareBitarray(5, _preserve=True)
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
    assert ConstantBitarray(True, 7) == Bitarray('1111111')
    assert ConstantBitarray(True, 7) != Bitarray('111111')
    assert ConstantBitarray(True, 7) != Bitarray('0000000')
    assert ConstantBitarray(False, 4) == Bitarray('0000')
    assert ConstantBitarray(False, 4) != Bitarray('000')
    assert ConstantBitarray(False, 4) != Bitarray('1111')

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

    c3 = Bitarray('1001')
    comp2 = CompositeBitarray(comp, c3)
    assert len(comp2) == 13
    assert comp2.__repr__() == "<CMP: TTTT?????1001 (13)>"

    #NOT TESTING __getitem__ much BECAUSE NOT USED
    #Does not respect nocare combining with prims...
    for i, bit in enumerate(Bitarray('1111000001001')):
        assert comp2[i] == bit

    with pytest.raises(IndexError):
        comp2[99]

    with pytest.raises(TypeError):
        comp2['INVALID']

    assert comp2.prepare() == Bitarray('1111111111001')
    assert comp2.prepare(preserve_history=True) == \
        Bitarray('1111111111001')

def test_composite_general_nocare_preserve():
    c1 = ConstantBitarray(True, 4)
    c2 = NoCareBitarray(5, _preserve=True)
    c3 = Bitarray('1001')
    comp = CompositeBitarray(c1, c2, c3)
    assert len(comp) == 13
    assert comp.__repr__() == "<CMP: TTTT?????1001 (13)>"

    assert comp.prepare() == Bitarray('1111111111001')
    assert comp.prepare(preserve_history=True) == \
        Bitarray('1111000001001')

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
    assert comp3.prepare() == Bitarray('11111111111')
    #PRESERVE
    c1 = NoCareBitarray(7, _preserve=True)
    comp = CompositeBitarray(c1)

    c2 = ConstantBitarray(True, 4)
    comp2 = CompositeBitarray(c2)

    comp3 = comp + comp2
    assert comp3.prepare(preserve_history=True) == Bitarray('00000001111')

def test_composite_any_all_count():
    c1 = NoCareBitarray(7)
    c2 = ConstantBitarray(True, 3)
    comp = CompositeBitarray(c1, c2)
    assert comp.any()
    assert not comp.all() #Maybe this will change later.

    c1 = Bitarray('111')
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

    c1 = Bitarray('111')
    c2 = ConstantBitarray(True, 3)
    comp = CompositeBitarray(c1, c2)
    assert comp.count(False) == c1.count(False)+c2.count(False)
    assert comp.count(True) == c1.count(True)+c2.count(True)

    c1 = NoCareBitarray(7)
    c2 = ConstantBitarray(False, 3)
    comp = CompositeBitarray(c1, c2)
    assert comp.count(False) == c1.count(False)+c2.count(False)
    assert comp.count(True) == c1.count(True)+c2.count(True)
