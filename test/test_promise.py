#-*- coding: utf-8 -*-
from proteusisc import Bitarray
from proteusisc.promise import TDOPromise, TDOPromiseCollection

class FakeChain(object):
    def __init__(self):
        self.hasflushed = False

    def flush(self):
        self.hasflushed = True

chain = FakeChain()

def test_promise_creation():
    pro = TDOPromise(chain, 0, 5)
    assert pro.bitstart == 0
    assert pro.bitlength == 5
    assert pro.bitend == 5

    pro = TDOPromise(chain, 4, 6)
    assert pro.bitstart == 4
    assert pro.bitlength == 6
    assert pro.bitend == 10

def test_promise_subpromises():
    pro = TDOPromise(chain, 0, 5)
    rest, tail = pro.split_to_subpromises()
    print(rest, tail)
    assert tail.bitstart == 0
    assert tail.bitlength == 1
    assert rest.bitstart == 0
    assert rest.bitlength == 4
    assert pro._components[0] == (rest, 0)
    assert pro._components[1] == (tail, 4)

    pro = TDOPromise(chain, 0, 1)
    rest, tail = pro.split_to_subpromises()
    assert rest == None
    assert tail == pro

def test_promise_fulfill():
    pro = TDOPromise(chain, 0, 5)
    pro._fulfill(Bitarray('10101'))
    assert pro() == Bitarray('10101')

    pro._fulfill(Bitarray('01010'))
    assert pro() == Bitarray('01010')

    #Check that splitting into two prims/promises
    #still fulfills correctly
    pro = TDOPromise(chain, 0, 5)
    rest, tail = pro.split_to_subpromises()
    tail._fulfill(Bitarray('1'))
    rest._fulfill(Bitarray('0101'))
    assert pro() == Bitarray('10101')

def test_promisecollection_creation():
    pro = TDOPromise(chain, 0, 8)
    promises = TDOPromiseCollection(chain, 8)
    assert not bool(promises)
    promises.add(pro, 0)
    assert bool(promises)

def test_promisecollection_fulfill():
    pro = TDOPromise(chain, 0, 8)
    promises = TDOPromiseCollection(chain, 8)
    promises.add(pro, 0)
    promises._fulfill(Bitarray('11001010'))
    assert pro() == Bitarray('11001010')

    pro = TDOPromise(chain, 0, 10)
    promises = TDOPromiseCollection(chain, 8)
    promises.add(pro, 2)
    promises._fulfill(Bitarray('0011001010'))
    assert pro() == Bitarray('11001010')


def test_promisecollection_split_fulfill():
    pro0 = TDOPromise(chain, 0, 8)
    pro1 = TDOPromise(chain, 0, 8)
    promises = TDOPromiseCollection(chain, 16)
    promises.add(pro0, 0)
    promises.add(pro1, 8)

    rest, tail = promises.split_to_subpromises()

    rest._fulfill(Bitarray('111111011001010'))
    tail._fulfill(Bitarray('1'))
    assert pro0() == Bitarray('11111110')
    assert pro1() == Bitarray('11001010')

def test_promisecollection_make_offset_sub():
    pro0 = TDOPromise(chain, 0, 8)
    pro1 = TDOPromise(chain, 0, 8)
    promises = TDOPromiseCollection(chain, 16)
    promises.add(pro0, 0)
    promises.add(pro1, 8)

    offsetpromises = promises.makesubatoffset(5)
    offsetpromises._fulfill(Bitarray('000001111111011001010'))
    assert pro0() == Bitarray('11111110')
    assert pro1() == Bitarray('11001010')

def test_promisecollection_make_offset_sub_with_ideal_tdo():
    pro0 = TDOPromise(chain, 0, 8)
    pro1 = TDOPromise(chain, 0, 8)
    promises = TDOPromiseCollection(chain, 24)
    promises.add(pro0, 0)
    promises.add(pro1, 16, _offsetideal=8)

    offsetpromises = promises.makesubatoffset(5, _offsetideal=0)
    print(offsetpromises)
    offsetpromises._fulfill(Bitarray('1111111011001010'),
                            ignore_nonpromised_bits=True)
    assert pro0() == Bitarray('11111110')
    assert pro1() == Bitarray('11001010')
