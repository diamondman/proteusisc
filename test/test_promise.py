#-*- coding: utf-8 -*-
from proteusisc.bittypes import bitarray
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
    assert len(pro) == 5
    assert pro.bitend == 5

    pro = TDOPromise(chain, 4, 6)
    assert pro.bitstart == 4
    assert len(pro) == 6
    assert pro.bitend == 10

def test_promise_split():
    pro = TDOPromise(chain, 0, 5)
    left, right = pro.split(1)
    print(right, left)
    assert left.bitstart == 0
    assert len(left) == 1
    assert right.bitstart == 0
    assert len(right) == 4
    assert pro._components[0] == (left, 0)
    assert pro._components[1] == (right, 1)


    pro = TDOPromise(chain, 0, 1)
    left, right = pro.split(1)
    assert left == pro
    assert right is None

def test_promise_fulfill():
    pro = TDOPromise(chain, 0, 5)
    pro._fulfill(bitarray('10101'))
    assert pro() == bitarray('10101')

    pro = TDOPromise(chain, 0, 5)
    pro._fulfill(bitarray('01010'))
    assert pro() == bitarray('01010')

def test_promise_split_fulfill():
    correct = bitarray('0011011111001')
    for i in range(len(correct)):
        print("Iteration", i)
        pro = TDOPromise(chain, 0, len(correct))
        cl, cr = correct[:i], correct[i:]

        l,r = pro.split(i)
        print(pro._components)
        print(l)
        print(r)
        if l:
            print("Load L", cl)
            l._fulfill(cl)
        if r:
            print("Load R", cr)
            r._fulfill(cr)
        assert pro() == correct
        print()

def test_composite_arbitrary_double_split_left():
    correct = bitarray('0011011111001')
    print("CORRECT", correct.to01())
    for i in range(1,len(correct)-1):
        cl, cr = correct[:i], correct[i:]
        for j in range(1, len(correct)-i):
            pro = TDOPromise(chain, 0, len(correct))
            l,r = pro.split(i)
            r1, r2 = r.split(j)
            cr1, cr2 = cr[:j], cr[j:]
            print("CORRECT", cl.to01(), cr1.to01(), cr2.to01())
            print("Processing", i, j)
            l._fulfill(cl)
            r1._fulfill(cr1)
            r2._fulfill(cr2)
            assert pro() == correct

def test_promise_double_split_right_fulfill():
    correct = bitarray('0011011111001')
    print("CORRECT", correct.to01())
    for i in range(len(correct)-1, 1, -1):
        for j in range(i-1, 0, -1):
            pro = TDOPromise(chain, 0, len(correct))
            cl, cr = correct[:i], correct[i:]
            cl1, cl2 = cl[:j], cl[j:]

            l,r = pro.split(i)
            l1, l2 = l.split(j)
            l1._fulfill(cl1)
            l2._fulfill(cl2)
            r._fulfill(cr)
            assert pro() == correct







def test_promisecollection_creation():
    pro = TDOPromise(chain, 0, 8)
    promises = TDOPromiseCollection(chain)
    assert not bool(promises)
    promises.add(pro, 0)
    assert bool(promises)

def test_promisecollection_make_offset_sub():
    pro0 = TDOPromise(chain, 0, 8)
    pro1 = TDOPromise(chain, 0, 8)
    promises = TDOPromiseCollection(chain)
    promises.add(pro0, 0)
    promises.add(pro1, 8)

    offsetpromises = promises.makesubatoffset(5)
    offsetpromises._fulfill(bitarray('000001111111011001010'))
    assert pro0() == bitarray('11111110')
    assert pro1() == bitarray('11001010')

def test_promisecollection_make_offset_sub_with_ideal_tdo():
    pro0 = TDOPromise(chain, 0, 8)
    pro1 = TDOPromise(chain, 0, 8)
    promises = TDOPromiseCollection(chain)
    promises.add(pro0, 0)
    promises.add(pro1, 16, _offsetideal=8)

    offsetpromises = promises.makesubatoffset(5, _offsetideal=0)
    print(offsetpromises)
    offsetpromises._fulfill(bitarray('1111111011001010'),
                            ignore_nonpromised_bits=True)
    assert pro0() == bitarray('11111110')
    assert pro1() == bitarray('11001010')


def test_promisecollection_fulfill():
    pro = TDOPromise(chain, 0, 8)
    promises = TDOPromiseCollection(chain)
    promises.add(pro, 0)
    promises._fulfill(bitarray('11001010'))
    assert pro() == bitarray('11001010')

    pro = TDOPromise(chain, 0, 10)
    promises = TDOPromiseCollection(chain)
    promises.add(pro, 2)
    promises._fulfill(bitarray('0011001010'))
    assert pro() == bitarray('11001010')

def test_promisecollection_nogaps_split_fulfill():
    correct = bitarray('1111111011001010')
    #DOES NOT AUTOSCALE TO LARGER DATA
    for i in range(len(correct)):
        print("Iteration", i)
        pro0 = TDOPromise(chain, 0, 8)
        pro1 = TDOPromise(chain, 0, 8)
        promises = TDOPromiseCollection(chain)
        promises.add(pro0, 0)
        promises.add(pro1, 8)

        cl, cr = correct[:i], correct[i:]

        l,r = promises.split(i)
        print("promises", promises._promises)
        print("L", l)
        print("R", r)
        if l:
            print("Load L", cl)
            l._fulfill(cl)
        if r:
            print("Load R", cr)
            r._fulfill(cr)
        assert pro0() == correct[:8]
        assert pro1() == correct[8:]
        print()

def test_promisecollection_gap_split_fulfill():
    indat = bitarray('111111100011001010')
    correct = bitarray('1111111011001010')
    #DOES NOT AUTOSCALE TO LARGER DATA
    for i in range(len(indat)):
        print("Iteration", i)
        pro0 = TDOPromise(chain, 0, 8)
        pro1 = TDOPromise(chain, 0, 8)
        promises = TDOPromiseCollection(chain)
        promises.add(pro0, 0)
        promises.add(pro1, 10)

        cl, cr = indat[:i], indat[i:]

        l,r = promises.split(i)
        print("promises", promises._promises)
        print("L", l)
        print("R", r)
        if l:
            print("Load L", cl)
            l._fulfill(cl)
        if r:
            print("Load R", cr)
            r._fulfill(cr)
        assert pro0() == correct[:8]
        assert pro1() == correct[8:]
        print()


def test_promisecollection_double_split_left_fulfill():
    correct = bitarray('1111111011001010')
    print("CORRECT", correct.to01())
    for i in range(1,len(correct)-1):
        cl, cr = correct[:i], correct[i:]
        for j in range(1, len(correct)-i):
            pro0 = TDOPromise(chain, 0, 8)
            pro1 = TDOPromise(chain, 0, 8)
            promises = TDOPromiseCollection(chain)
            promises.add(pro0, 0)
            promises.add(pro1, 8)

            l,r = promises.split(i)
            r1, r2 = r.split(j)
            cr1, cr2 = cr[:j], cr[j:]
            l._fulfill(cl)
            r1._fulfill(cr1)
            r2._fulfill(cr2)
            assert pro0() == correct[:8]
            assert pro1() == correct[8:]

def test_promisecollection_double_split_right_fulfill():
    correct = bitarray('1111111011001010')
    print("CORRECT", correct.to01())
    for i in range(len(correct)-1, 1, -1):
        for j in range(i-1, 0, -1):
            pro0 = TDOPromise(chain, 0, 8)
            pro1 = TDOPromise(chain, 0, 8)
            promises = TDOPromiseCollection(chain)
            promises.add(pro0, 0)
            promises.add(pro1, 8)

            cl, cr = correct[:i], correct[i:]
            cl1, cl2 = cl[:j], cl[j:]

            l,r = promises.split(i)
            l1, l2 = l.split(j)

            l1._fulfill(cl1)
            l2._fulfill(cl2)
            r._fulfill(cr)
            assert pro0() == correct[:8]
            assert pro1() == correct[8:]
