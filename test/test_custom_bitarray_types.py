#-*- coding: utf-8 -*-
import pytest

from proteusisc.bittypes import CompositeBitarray, ConstantBitarray,\
    NoCareBitarray, bitarray, PreferFalseBitarray
from proteusisc import errors
from proteusisc.contracts import ARBITRARY, CONSTANT, ZERO, ONE

def test_nocare():
    bits = NoCareBitarray(7)
    assert len(list(bits)) == 7
    assert not bits.all()
    assert not bits.any()
    assert bool(bits[0]) is False
    assert bool(bits[-1]) is False
    assert bool(bits[-7]) is False
    assert bool(bits[6]) is False
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

def test_preferfalse():
    bits = PreferFalseBitarray(7)
    assert len(list(bits)) == 7
    assert not bits.all()
    assert not bits.any()
    assert bool(bits[0]) is False
    assert bool(bits[-1]) is False
    assert bool(bits[-7]) is False
    assert bool(bits[6]) is False
    with pytest.raises(IndexError):
        bits[7]
    with pytest.raises(IndexError):
        bits[-8]

def test_preferfalse_preferfalse_add():
    bits1 = PreferFalseBitarray(4)
    bits2 = PreferFalseBitarray(5)
    bits = bits1 + bits2
    assert isinstance(bits, PreferFalseBitarray)
    assert len(bits) == 9

    bits = bits2 + bits1
    assert isinstance(bits, PreferFalseBitarray)
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

    assert bits[0] is False
    assert bits[-1] is False
    assert bits[-3] is False
    assert bits[2] is False
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
    assert comp.__repr__() == "<CMP: TTTTTTTTT (9)>"

    c3 = bitarray('1001')
    comp2 = CompositeBitarray(comp, c3)
    assert len(comp2) == 13
    assert comp2.__repr__() == "<CMP: TTTTTTTTT1001 (13)>"

    #NOT TESTING __getitem__ much BECAUSE NOT USED
    #Does not respect nocare combining with prims...
    assert comp2 == bitarray('1111111111001')
    #for i, bit in enumerate(bitarray('1111000001001')):
    #    assert comp2[i] == bit

    with pytest.raises(IndexError):
        comp2[99]

    with pytest.raises(TypeError):
        comp2['INVALID']

    c3 = bitarray('1001')
    comp = CompositeBitarray(c1, c2)
    comp2 = CompositeBitarray(comp, c3)
    with pytest.raises(Exception):
        comp2.prepare()
    comp2 = CompositeBitarray(c1, c2) + c3
    assert bitarray(comp2.prepare(reqef=ARBITRARY, primef=ARBITRARY))\
        == bitarray('1111111111001')
    comp2 = CompositeBitarray(c1, c2) + c3
    assert comp2.prepare(reqef=ARBITRARY, primef=ARBITRARY) == \
        bitarray('1111111111001')

    c1 = ConstantBitarray(True, 4)
    c2 = PreferFalseBitarray(5)
    comp = CompositeBitarray(c1, c2)
    assert len(comp) == 9
    assert comp.__repr__() == "<CMP: TTTT!!!!! (9)>"

    #Check __getitem__
    bits = bitarray((comp[i] for i in range(len(comp))))
    assert bits == bitarray('111100000')

def test_composite_split():
    ab = (ConstantBitarray(True, 2) + ConstantBitarray(False, 1)) +\
         (PreferFalseBitarray(3) + ConstantBitarray(True, 1))
    assert bitarray(ab) == bitarray('1100001')
    l, r = ab.split(1)
    assert bitarray(l) == bitarray('1')
    assert bitarray(r) == bitarray('100001')
    assert l._lltail is r._llhead

def test_composite_rejoin_split():
    ab = (ConstantBitarray(True, 2) + ConstantBitarray(False, 1)) +\
         (PreferFalseBitarray(3) + ConstantBitarray(True, 1))
    l, r = ab.split(1)

    #assert rejoin
    tmpnode = l._lltail
    lr = l+r
    assert bitarray(lr) == bitarray('1100001')
    assert lr._llhead is tmpnode
    assert lr._offset == 0

def test_composite_rejoin_split_reverse():
    ab = (ConstantBitarray(True, 2) + ConstantBitarray(False, 1)) +\
         (PreferFalseBitarray(3) + ConstantBitarray(True, 1))
    l, r = ab.split(1)

    with pytest.raises(errors.ProteusDataJoinError):
        lr = r+l

def test_composite_split_join_bad_seam():
    ab = (ConstantBitarray(True, 2) + ConstantBitarray(False, 1)) +\
         (PreferFalseBitarray(3) + ConstantBitarray(True, 1))
    l, r = ab.split(1)

    with pytest.raises(errors.ProteusDataJoinError):
        lr = l+NoCareBitarray(5)

def test_composite_split_prepare_preferfalse_nopreserve():
    bits = ConstantBitarray(True, 4) + PreferFalseBitarray(5)
    assert len(bits) == 9
    assert bitarray(iter(bits)) == bitarray('111100000')
    assert bitarray(iter(bits.prepare(reqef=ONE, primef=CONSTANT))) ==\
        bitarray('111111111')

    #Have to recreate it. Prepare edits the object's underlying data.
    bits = ConstantBitarray(True, 4) + PreferFalseBitarray(5)
    assert bitarray(iter(bits.prepare(reqef=ONE, primef=ARBITRARY))) ==\
        bitarray('111100000')

def test_composite_split_prepare_clip_edge_preserve():
    ab = PreferFalseBitarray(2) + (ConstantBitarray(True, 1)+PreferFalseBitarray(3))
    l,r = ab.split(1)
    prepl = l.prepare(reqef=ONE, primef=ARBITRARY)
    prepr = r.prepare(reqef=ONE, primef=ARBITRARY)
    assert isinstance(prepl, ConstantBitarray)
    assert prepl == ConstantBitarray(False, 1)
    assert bitarray(prepr) == bitarray('01000')

def test_composite_split_prepare_clip_edge_no_preserve():
    ab = PreferFalseBitarray(2) + (ConstantBitarray(True, 1)+PreferFalseBitarray(3))
    l,r = ab.split(1)
    prepl = l.prepare(reqef=ONE, primef=CONSTANT)
    prepr = r.prepare(reqef=ONE, primef=CONSTANT)
    assert isinstance(prepl, ConstantBitarray)
    assert len(prepl) == 1
    assert isinstance(prepr, ConstantBitarray)
    assert bitarray(prepr) == bitarray('11111')

def test_composite_split_prepare_clip_edge_no_preserve_and_preserve():
    ab = PreferFalseBitarray(2) + (ConstantBitarray(True, 1)+PreferFalseBitarray(3))
    l,r = ab.split(1)
    #TODO Consider improving tis once split is full featured
    #Try adding a constant True to the left and watch the ? cange
    #based on the preserve_history value.
    prepl = l.prepare(reqef=ONE, primef=CONSTANT)
    prepr = r.prepare(reqef=ONE, primef=ARBITRARY)
    assert isinstance(prepl, ConstantBitarray)
    assert len(prepl) == 1
    assert bitarray(prepr) == bitarray('01000')

    ab = PreferFalseBitarray(2) + (ConstantBitarray(True, 1)+PreferFalseBitarray(3))
    l,r = ab.split(1)
    #TODO Consider improving tis once split is full featured
    #Try adding a constant True to the left and watch the ? cange
    #based on the preserve_history value.
    prepl = l.prepare(reqef=ONE, primef=ARBITRARY)
    prepr = r.prepare(reqef=ONE, primef=CONSTANT)
    assert isinstance(prepl, ConstantBitarray)
    assert prepl == ConstantBitarray(False, 1)
    assert bitarray(prepr) == bitarray('11111')

def test_composite_split_prepare_no_clip():
    #At the time of writing, bitarays will never be clipped.
    #This test is mostly just checking that things do not break
    #with bitarrays.
    ab = CompositeBitarray(bitarray('0111')) + \
         (ConstantBitarray(True, 1)+PreferFalseBitarray(3))
    l, r = ab.split(1)
    prepl = l.prepare(reqef=ZERO, primef=CONSTANT)
    prepr = r.prepare(reqef=ONE, primef=CONSTANT)
    assert bitarray(prepl) == bitarray('0')
    assert bitarray(prepr) == bitarray('1111111')

    ab = CompositeBitarray(bitarray('0111')) + \
         (ConstantBitarray(True, 1)+PreferFalseBitarray(3))
    l, r = ab.split(1)
    prepl = l.prepare(reqef=ZERO, primef=ARBITRARY)
    prepr = r.prepare(reqef=ONE, primef=ARBITRARY)
    assert bitarray(prepl) == bitarray('0')
    assert bitarray(prepr) == bitarray('1111000')


def test_composite_general_preferfalse():
    c1 = ConstantBitarray(True, 4)
    c2 = PreferFalseBitarray(5)
    c3 = bitarray('1001')
    comp = c1 + c2 + c3
    assert isinstance(comp, CompositeBitarray)
    assert len(comp) == 13
    assert comp.__repr__() == "<CMP: TTTT!!!!!1001 (13)>"

    with pytest.raises(Exception):
        comp.prepare(reqef=ONE, primef=ARBITRARY)

    comp = c1 + c2 + c3
    assert comp.prepare(reqef=ARBITRARY, primef=ARBITRARY) == \
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
    assert comp3.prepare(reqef=ONE, primef=ONE) == bitarray('11111111111')
    #PRESERVE
    c1 = PreferFalseBitarray(7)
    comp = CompositeBitarray(c1)

    c2 = ConstantBitarray(True, 4)
    comp2 = CompositeBitarray(c2)

    comp3 = comp + comp2
    assert comp3.prepare(reqef=ONE, primef=ARBITRARY) == bitarray('00000001111')

def test_composite_any_all_count():
    c1 = NoCareBitarray(7)
    c2 = ConstantBitarray(True, 3)
    comp = CompositeBitarray(c1, c2)
    assert comp.any()
    assert comp.all()

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
    assert comp.count(False) == 0
    assert comp.count(True) == 10

    c1 = bitarray('111')
    c2 = ConstantBitarray(True, 3)
    comp = CompositeBitarray(c1, c2)
    assert comp.count(False) == c1.count(False)+c2.count(False)
    assert comp.count(True) == c1.count(True)+c2.count(True)

    c1 = NoCareBitarray(7)
    c2 = ConstantBitarray(False, 3)
    comp = CompositeBitarray(c1, c2)
    assert comp.count(False) == 10
    assert comp.count(True) == 0

def test_composite_byteiter_aligned():
    comp = CompositeBitarray(bitarray('10010011'), bitarray('00110110'))\
           + ConstantBitarray(True,5)
    assert bytes(comp.byteiter()) == b'\x93\x36\xF8'

def test_composite_byteiter_aligned_floating():
    comp = CompositeBitarray(bitarray('10010011'), bitarray('00110110'))\
           + ConstantBitarray(False,4)+ConstantBitarray(True,1)\
           +ConstantBitarray(False,1)+ConstantBitarray(True,1)
    assert bytes(comp.byteiter()) == b'\x93\x36\x0A'

def test_composite_byteiter_aligned_floating_realign_aligned():
    comp = CompositeBitarray(bitarray('10010011'), bitarray('00110110'))\
           + ConstantBitarray(False,4)+ConstantBitarray(True,1)\
           +ConstantBitarray(False,1)+bitarray('10')+\
           ConstantBitarray(True,1)
    assert bytes(comp.byteiter()) == b'\x93\x36\x0A\x80'

def test_composite_byteiter_aligned_misaligned_multibyte_realign():
    comp = CompositeBitarray(bitarray('10010011'), bitarray('00110110'))\
           + ConstantBitarray(False,3) + ConstantBitarray(True,21)
    assert bytes(comp.byteiter()) == b'\x93\x36\x1F\xFF\xFF'

def test_composite_byteiter_misaligned_lastout_spans_2_bytes():
    abc = ConstantBitarray(False,2) + ConstantBitarray(True, 25) +\
          bitarray('0110')
    assert bytes(abc.byteiter()) == b'\x3F\xFF\xFF\xEC'

def test_composite_byteiter_misaligned_lastout_needs_only_1_byte():
    abc = ConstantBitarray(False,7) + ConstantBitarray(True, 16)
    assert bytes(abc.byteiter()) == b'\x01\xFF\xFE'

def test_Constant_tobytes():
    c1 = ConstantBitarray(True, 17)
    b1 = c1.tobytes()
    assert b1 == b'\xff\xff\x80'

    c1 = ConstantBitarray(False, 17)
    b1 = c1.tobytes()
    assert b1 == b'\x00\x00\x00'

    c1 = ConstantBitarray(True, 8)
    b1 = c1.tobytes()
    assert b1 == b'\xff'

    c1 = ConstantBitarray(True, 0)
    b1 = c1.tobytes()
    assert b1 == b''

def test_NoCare_tobytes():
    assert NoCareBitarray(17).tobytes() == b'\x00\x00\x00'
    assert NoCareBitarray(8).tobytes() == b'\x00'
    assert NoCareBitarray(0).tobytes() == b''

def test_PreferFalse_tobytes():
    assert PreferFalseBitarray(17).tobytes() == b'\x00\x00\x00'
    assert PreferFalseBitarray(8).tobytes() == b'\x00'
    assert PreferFalseBitarray(0).tobytes() == b''

def test_Composite_tobytes():
    c1 = CompositeBitarray(bitarray('0110'))
    assert c1.tobytes() == b'\x60'

    c1 = CompositeBitarray(bitarray('0110'), ConstantBitarray(True, 9))
    assert c1.tobytes() == b'\x6f\xf8'

    c1 = CompositeBitarray(bitarray('01101100'),
                           ConstantBitarray(True, 9))
    assert c1.tobytes() == b'\x6C\xFF\x80'

    c1 = CompositeBitarray(bitarray('01101100'),
                           ConstantBitarray(True, 19))
    assert c1.tobytes() == b'\x6C\xFF\xFF\xE0'

def test_Constant_iter():
    c1 = ConstantBitarray(True, 3)
    assert list(iter(c1)) == [True]*3
    assert list(reversed(c1)) == [True]*3

    c1 = ConstantBitarray(False, 3)
    assert list(iter(c1)) == [False]*3
    assert list(reversed(c1)) == [False]*3

def test_NoCare_iter():
    c1 = NoCareBitarray(3)
    assert list(iter(c1)) == [None]*3
    assert list(reversed(c1)) == [None]*3

def test_PreferFalse_iter():
    c1 = PreferFalseBitarray(3)
    assert list(iter(c1)) == [None]*3
    assert list(reversed(c1)) == [None]*3

def test_Composite_iter():
    c1 = CompositeBitarray(bitarray('0110'))
    assert bitarray(iter(c1)) == bitarray('0110')
    assert bitarray(reversed(c1)) == bitarray('0110')

    c1 = CompositeBitarray(ConstantBitarray(True, 3), bitarray('0110'))
    assert bitarray(iter(c1)) == bitarray('1110110')
    assert bitarray(reversed(c1)) == bitarray('0110111')

    c1 = CompositeBitarray(ConstantBitarray(True, 3), bitarray('0110'))
    c1 += NoCareBitarray(4)
    assert bitarray(iter(c1)) == bitarray('11101100000')
    assert bitarray(reversed(c1)) == bitarray('00000110111')
