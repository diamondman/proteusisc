#-*- coding: utf-8 -*-
from bitarray import bitarray

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

def test_promise_fulfill():
    pro = TDOPromise(chain, 0, 5)
    pro._fulfill(bitarray('10101'))
    assert pro() == bitarray('10101')

    pro._fulfill(bitarray('01010'))
    assert pro() == bitarray('01010')

    #Check that splitting into two prims/promises
    #still fulfills correctly
    pro = TDOPromise(chain, 0, 5)
    rest, tail = pro.split_to_subpromises()
    tail._fulfill(bitarray('1'))
    rest._fulfill(bitarray('0101'))
    assert pro() == bitarray('10101')

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
    promises._fulfill(bitarray('11001010'))
    assert pro() == bitarray('11001010')

    pro = TDOPromise(chain, 0, 10)
    promises = TDOPromiseCollection(chain, 8)
    promises.add(pro, 2)
    promises._fulfill(bitarray('0011001010'))
    assert pro() == bitarray('11001010')


def test_promisecollection_split_fulfill():
    pro0 = TDOPromise(chain, 0, 8)
    pro1 = TDOPromise(chain, 0, 8)
    promises = TDOPromiseCollection(chain, 16)
    promises.add(pro0, 0)
    promises.add(pro1, 8)

    rest, tail = promises.split_to_subpromises()

    rest._fulfill(bitarray('111111011001010'))
    tail._fulfill(bitarray('1'))
    assert pro0() == bitarray('11111110')
    assert pro1() == bitarray('11001010')

def test_promisecollection_make_offset_sub():
    pro0 = TDOPromise(chain, 0, 8)
    pro1 = TDOPromise(chain, 0, 8)
    promises = TDOPromiseCollection(chain, 16)
    promises.add(pro0, 0)
    promises.add(pro1, 8)

    offsetpromises = promises.makesubatoffset(5)
    offsetpromises._fulfill(bitarray('000001111111011001010'))
    assert pro0() == bitarray('11111110')
    assert pro1() == bitarray('11001010')
