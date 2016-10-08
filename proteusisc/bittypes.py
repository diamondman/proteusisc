from __future__ import generator_stop
from itertools import islice
import collections
from bitarray import bitarray
import math

class Bitarray(bitarray):#collections.Sequence):
    #def __init__(self, initial):
    #    if isinstance(initia, bitarray):
    #        self._val = initial
    #    else:
    #        self._val = bitarray(initial)
    #
    #def __repr__(self):
    #    return "<BA %s>"%self._val.__repr__()

    def __add__(self, other):
        if len(self) == 0:
            return other
        if len(other) == 0:
            return self
        if isinstance(other, (ConstantBitarray, NoCareBitarray,
                              Bitarray)):
            return CompositeBitarray(self, other)
        return NotImplemented

    def __radd__(self, other):
        if len(self) == 0:
            return other
        if len(other) == 0:
            return self
        if isinstance(other, (ConstantBitarray, NoCareBitarray)):
            return CompositeBitarray(other, self)
        return NotImplemented


class ConstantBitarray(collections.Sequence):
    """A bitarray type where all bits are the same value.

    The bitarray class is already more efficient at storing a sequence
    of boolean values than an array, but all bits having the same
    value is a common enough case to optimize for.

    The most immediate obvious is a lower memory footprint, as only
    one boolean value is stored. But there are more important benefits.

    Splitting or reversing a constant bitarray, or combining two
    constant bitarrays (that have the same value) is trivial.

    Checking if any or all bits are set is trivial (A normal bitarray
    has to scan every bit every time such a check is done).

    A constant bitarray shows intent. By simply checking the type of
    the bitarray, we can know if sending the data in the bitarray down
    a wire requires arbitrary control of the signal value for every
    bit, of if we can get away with a simplier constant value.

    Args:
        val: A boolean that will be the value for each bit in the array.
        length: An integer specifying how many bits are in the array.
    """
    def __init__(self, val, length):
        self._val = bool(val)
        self._length = length

    def __len__(self):
        return self._length
    def __getitem__(self, index):
        #import ipdb
        #ipdb.set_trace()
        if isinstance(index, slice):
            indices = index.indices(len(self))
            return ConstantBitarray(self._val, len(range(*indices)))

        if isinstance(index, int):
            index = len(self)-abs(index) if index < 0 else index
            if (index < self._length and index >= 0):
                return self._val
            raise IndexError("%s index out of range"%type(self))
        raise TypeError("%s indices must be integers or slices, not %s"%
                        (type(self), type(index)))
    def __repr__(self):
        return "<Const: %s (%s)>"%\
            (self._val, self._length)# pragma: no cover

    def __add__(self, other):
        """Handles combining different bitarray types.

        There are special rules for combining each type of bitarray:
        bitarray, ConstantBitarray, and NoCareBitArray. For example,
        two NoCareBitarrays combine into a bigger NoCareBit array,
        while combining two ConstantBitArrays depends on if the two
        array's constant value are the same.
        """
        if len(self) == 0:
            return other
        if len(other) == 0:
            return self
        if isinstance(other, ConstantBitarray):
            if self._val == other._val:
                return ConstantBitarray(self._val,
                                        self._length+other._length)
            return CompositeBitarray(self, other)
        #if isinstance(other, bitarray):
        #    return CompositeBitarray(self, other)
        return NotImplemented

    def __iter__(self):
        for bit in range(self._length):
            yield self._val

    def __reversed__(self):
        for bit in range(self._length):
            yield self._val

    def __eq__(self, other):
        if isinstance(other, ConstantBitarray):
            return len(self) == len(other) and self._val == other._val
        if isinstance(other, Bitarray):
            if len(self) != len(other):
                return False
            if self._val:
                return other.all()
            else:
                return not other.any()
        return NotImplemented

    def count(self, val=True):
        """Get the number of bits in the array with the specified value.

        Args:
            val: A boolean value to check against the array's value.

        Returns:
            An integer of the number of bits in the array equal to val.
        """
        if val == self._val:
            return self._length
        return 0

    def any(self):
        return self._val

    def all(self):
        return self._val

    def tobytes(self):
        if not len(self):
            return b''
        if self._val:
            if len(self)%8:
                return bytes([0xFF]*(math.ceil(len(self)/8)-1)+\
                             [(0xFF<<(8-len(self)%8))&0xFF])
            return bytes([0xFF]*(math.ceil(len(self)/8)))

        return bytes([0x00]*(math.ceil(len(self)/8)))

    def reverse(self):
        pass

class NoCareBitarray(collections.Sequence):
    """A bitarray type with no preference on its bit values.

    https://en.wikipedia.org/wiki/Don%27t-care_term

    When writing data to certain fields, sometimes the value of the
    field simply does not matter. In programming, we often fill 0 or
    Null for these values because the cost of any of these filler
    values are the same. If such an no care parameter were set to 0,
    but setting it to 1 would somehow let the computer run the program
    faster, it would be a clear win.

    But the computer can not tell that the 0 put as a place holder is
    JUST a placeholder.

    In this project, parameters passed over a serial datastream are
    often represented with the type bitarray.bitarray. To allow
    optimizing the sending of data, the NoCareBitarray explicitly
    stands in for a sequence of bits where the value does not matter,
    so that as it is combined with other bits, a more efficient (by
    some metric) sequence of bits can be produced than if strict
    adherence to a placeholder value were held.

    Like ConstantBitarrays, NoCareBitarrays have a small memory
    footprint, and are efficiently combined, sliced, and checked for
    values.

    A nocare bitarray shows intent. By simply checking the type of the
    bitarray, we can know if sending the data in the bitarray down a
    wire requires have any requirements at all, or if the bits are
    free to be optimized aggressively without danger of losing useful
    data.

    Args:
        length: An integer specifying how many bits are in the array.

    """
    def __init__(self, length):
        self._length = length

    def __len__(self):
        return self._length
    def __getitem__(self, index):
        #import ipdb
        #ipdb.set_trace()
        if isinstance(index, slice):
            indices = index.indices(len(self))
            return NoCareBitarray(len(range(*indices)))

        if isinstance(index, int):
            index = len(self)-abs(index) if index < 0 else index
            if (index < self._length and index >= 0):
                return False
            raise IndexError("%s index out of range"%type(self))
        raise TypeError("%s indices must be integers or slices, not %s"%
                        (type(self), type(index)))

    def __iter__(self):
        for _ in range(self._length):
            yield False

    def __reversed__(self):
        for _ in range(self._length):
            yield False

    def __repr__(self):
        return "<NC: (%s)>"%self._length # pragma: no cover

    def __add__(self, other):
        """Handles combining different bitarray types.

        There are special rules for combining each type of bitarray:
        bitarray, ConstantBitarray, and NoCareBitArray. For example,
        two NoCareBitarrays combine into a bigger NoCareBit array,
        while combining two ConstantBitArrays depends on if the two
        array's constant value are the same.
        """
        if isinstance(other, bool):
            return NotImplemented
        if len(self) == 0:
            return other
        if len(other) == 0:
            return self

        if isinstance(other, NoCareBitarray):
            return NoCareBitarray(self._length+other._length)
        if isinstance(other, ConstantBitarray):
            if not other._val:
                return ConstantBitarray(False, self._length+other._length)
            return CompositeBitarray(self, other)
        return NotImplemented

    def __radd__(self, other):
        if isinstance(other, bool):
            return NotImplemented
        if len(self) == 0:
            return other
        if len(other) == 0:
            return self

        if isinstance(other, ConstantBitarray):
            if not other._val:
                return ConstantBitarray(False, self._length+other._length)
            return CompositeBitarray(other, self)
        return NotImplemented

    def count(self, val=True):
        """Get the number of bits in the array with the specified value.

        Args:
            val: A boolean value to check against the array's value.

        Returns:
            An integer of the number of bits in the array equal to val.
        """
        return 0

    def any(self):
        return False

    def all(self):
        return False

    def tobytes(self):
        if not len(self):
            return b''
        return bytes([0x00]*(math.ceil(len(self)/8)))

    def reverse(self):
        pass


class CompositeBitarray(collections.Sequence):
    """A container to hold multiple bitarray types without actually combining them and losing information about which bits are NoCare.

    Most bits marked as No Care have no negative effect if the bits
    assume either True or False. If a ConstantBitArray(True,...) is
    added to a NoCareBitarray(...), the result will be a
    ConstantBitArray with a value of True and the length of both
    component bitarrays. This is fine for TDI and TMS bits, but not
    acceptable for TDO bits.

    For primitives that support arbitrary tdo bits, the No Care bits
    that were added to the sequence should turn into False bits, which
    is violated in the addition demonstrated above (the NoCare bits
    are not retrievable from the combined ConstantBitArray).

    The current solution is to build a bitarray class that keeps track
    of the component bitarrays that would normally have been merged
    together. These components stay split until the point the
    'prepare' method is called. Arguments to 'prepare' specify if the
    associated primitive supports arbitrary TDO data or not, so the
    combination of data can take into account if the NoCare bits
    should be converted to False or True.

    """
    #@profile
    def __init__(self, component1=None, component2=None,
                 *, offset=0, tailoffset=0):
        """Create a bitarray object that stores its components by reference).

        Args:
            *components: Any number of bitarray instances to store in this composition.
        """
        #TODO Check if this lookup structure causes slowdown.
        self._llhead = None
        self._lltail = None
        self._length = -offset-tailoffset
        self._offset = offset
        self._tailoffset = tailoffset

        #if isinstance(component1, CompositeBitarray) and \
        #   isinstance(component2, CompositeBitarray):

        if component1 is None and component2 is not None:
            component1 = component2
            component2 = None

        if component1 is None:
            return
        elif isinstance(component1, CompositeBitarray):
            self._length += len(component1)
            if self._offset == len(component1._llhead.value):
                self._llhead = component1._llhead.next
            else:
                self._llhead = component1._llhead
            self._lltail = component1._lltail
            self._offset += component1._offset
        else:
            self._length += len(component1)
            self._llhead = _DLLNode(component1)
            self._lltail = self._llhead

        #print(list(self._iter_components()))

        #import ipdb
        #ipdb.set_trace()

        if component2 is None:
            pass
        elif isinstance(component2, CompositeBitarray):
            if self._lltail is component2._llhead:
                #TODO Figure out why offset/tailoffset is not right
                #self._length += len(component2) -
                assert component1._tailoffset + component2._offset ==\
                    len(component1._lltail.value),\
                    "Linkedlist pieces recombined not along seam."
                self._lltail = component2._lltail
                self._tailoffset = component2._tailoffset
                self._length = len(component1)+len(component2)
                #self._length = sum(len(elem) for elem in
                #                   self._iter_components()) -\
                #                   (self._offset+self._tailoffset)
                #assert self._length == len(component1)+len(component2),\
                #    "%s != %s"%(sekf._length,
                #                len(component1)+len(component2))
            else:
                self._length += len(component2)
                self._lltail.next = component2._llhead
                #self._lltail._next = component2._llhead
                #component2._llhead._prev = self._lltail
                self._lltail = component2._lltail
        else:
            self._length += len(component2)
            node = _DLLNode(component2)
            node.prev = self._lltail
            #node._prev = self._lltail
            #self._lltail._next = node
            self._lltail = node

    def _iter_components(self):
        for elem in self._llhead.iternexttill(self._lltail):
            yield elem.value

    def __len__(self):
        return self._length
    def __getitem__(self, index):
        """Get a value at an index from the composite bitarray

        Since the actual bit values are stored in an array of arrays,
        the array of components has to be searched to find the correct
        sub array (and its offset) to look for the index.

        This functions is used exceedingly rarely, since most data
        extraction is done with 'prepare'. If this method starts being
        used more, it will be necessary to change the underlying data
        type to some kind of tree, or support an efficient iterator.

        Args:
            index: An int bit number to look up in the combined bits of all components.

        Return:
            A boolean value of the bit looked up.

        """
        #import ipdb
        #ipdb.set_trace()
        if index == slice(1, None, None):
            return CompositeBitarray(self, offset=1)
        if index == 0:
            res = CompositeBitarray()
            res._length = 1
            res._llhead = self._llhead
            res._lltail = self._llhead
            res._tailoffset = len(res._lltail.value)-1
            return res
        if isinstance(index, int):
        #    index = len(self)-abs(index) if index < 0 else index
        #    print("Reading a CompositeBitarray bit",index)
        #    if (index < self._length and index >= 0):
        #        r, elem = self._lookup_range(index)
        #        return elem[index-r.start]
        #    raise IndexError("%s index out of range"%type(self))
            raise IndexError("No support for non 0 ints for now.")
        raise TypeError("%s indices must be integers, not %s"%
                        (type(self), type(index)))
    def __str__(self):
        return "".join(['?' if isinstance(elem, NoCareBitarray) else
                        (('T' if b else 'F') if isinstance(elem,
                                                    ConstantBitarray)
                         else ('1' if b else '0'))
                        for elem in self._iter_components()
                        for b in elem])\
                            [self._offset:-self._tailoffset or None]
    def __repr__(self):
        return "<CMP: %s (%s)>"%\
            (str(self), self._length)# pragma: no cover

    #@profile
    def __add__(self, other):
        if isinstance(other, (CompositeBitarray, ConstantBitarray,
                              NoCareBitarray, Bitarray)):
            return CompositeBitarray(self, other)
        return NotImplemented
    #@profile
    def __radd__(self, other):
        if isinstance(other, (ConstantBitarray, NoCareBitarray,
                              Bitarray)):
            return CompositeBitarray(other, self)
        return NotImplemented

    def __iter__(self):
        #TODO Not handling a single item with offset and tailoffset
        cnt = 0
        node = self._llhead
        for bit in islice(node.value, self._offset, None):
            cnt += 1
            if cnt > len(self):
                import ipdb
                ipdb.set_trace()
                raise Exception("SHIT! LOOPED TILL %s; End %s"%\
                                (cnt, len(self)))
            yield bit
        if node is self._lltail:
            return

        while True:
            node = node.next
            if node is self._lltail:
                break
            for bit in node.value:
                cnt += 1
                if cnt > len(self):
                    import ipdb
                    ipdb.set_trace()
                    raise Exception("SHIT! LOOPED TILL %s; End %s"%\
                                    (cnt, len(self)))
                yield bit

        for bit in islice(node.value, None, -self._tailoffset or None):
            cnt += 1
            if cnt > len(self):
                import ipdb
                ipdb.set_trace()
                raise Exception("SHIT! LOOPED TILL %s; End %s"%\
                                (cnt, len(self)))
            yield bit

    def __reversed__(self):
        #TODO Not handling a single item with offset and tailoffset
        node = self._lltail
        ptiter = reversed(node.value)
        for _ in range(self._tailoffset):
            next(ptiter)
        #if node is self._llhead:
        #    for _ in range(self._tailoffset,
        #                   len(node.value)-self._offset):
        #        yield next(ptiter)
        #    return
        #else:
        for bit in ptiter:
            yield bit

        while True:
            node = node.prev
            if node is self._llhead:
                break
            for bit in reversed(node.value):
                yield bit

        ptiter = reversed(node.value)
        for _ in range(len(node.value)-self._offset):
            yield next(ptiter)


    def count(self, val=True):
        """Get the number of bits in the array with the specified value.

        Args:
            val: A boolean value to check against the array's value.

        Returns:
            An integer of the number of bits in the array equal to val.
        """
        return sum((elem.count(val) for elem in self._iter_components()))

    def any(self):
        return any((elem.any() for elem in self._iter_components()))

    def all(self):
        return all((elem.all() for elem in self._iter_components()))

    def prepare(self, *, preserve_history=False):
        """Extract the composite array's data into a usable bitarray based on if NoCare bits should be rendered as True or False.

        This method does the heavy lifting of producing a bitarray
        that is more efficient for tdo bits when that optimization is
        available.

        KWArgs:
            preserve_history: A bool, True means No Care bits render as Fakse.

        Returns:
            A bitarray that is the combined result of all the composite bitarray's components.

        """
        res = NoCareBitarray(0)
        for elem in self._llhead.iternexttill(self._lltail):
            if isinstance(elem, NoCareBitarray):
                if preserve_history:
                    res += ConstantBitarray(False, len(elem.value))
                else:
                    res += elem.value
            else:
                res += elem.value
        return res

    def tobytes(self):
        tmpba = bitarray(self)
        return tmpba.tobytes()


class _DLLNode(object):
    def __init__(self, value):
        self._value = value
        self._next = None
        self._prev = None

    @property
    def next(self):
        return self._next
    @next.setter
    def next(self, node):
        if self is node:
            raise ValueError("Invalid next node. Infinite Loop")
        self._next = node
        node._prev = self

    @property
    def prev(self):
        return self._prev
    @prev.setter
    def prev(self, node):
        if self is node:
            raise ValueError("Invalid prev node. Infinite Loop")
        self._prev = node
        node._next = self

    @property
    def value(self):
        return self._value

    def iternexttill(self, target):
        node = self
        while True:
            yield node
            if node is target:
                break
            node = node.next

    def iterprevtill(self, target):
        node = self
        while True:
            yield node
            if node is target:
                break
            node = node.prev

    def __repr__(self):
        return "Node(%s%s)"%\
            (self.value[:32], "..." if len(self.value)>32 else "")
