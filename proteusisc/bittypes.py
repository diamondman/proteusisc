from __future__ import generator_stop
from itertools import islice
import collections
from bitarray import bitarray as _bitarray
import math

from .errors import ProteusDataJoinError
from .contracts import ZERO, ONE, NOCARE, ARBITRARY

class bitarray(_bitarray):
    def _easy_mergable(self, other):
        return False #Consider merging single bit bitarrays.

    def byteiter(self):
        data = self.tobytes()
        for byte in data:
            yield byte

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
        if isinstance(other, bitarray):
            return CompositeBitarray(self, other)
        return NotImplemented

    def __radd__(self, other):
        if isinstance(other, bitarray):
            return CompositeBitarray(other, self)
        return NotImplemented

    def __iter__(self):
        for _ in range(self._length):
            yield self._val

    def __reversed__(self):
        for _ in range(self._length):
            yield self._val

    def __eq__(self, other):
        if isinstance(other, ConstantBitarray):
            return len(self) == len(other) and self._val == other._val
        if isinstance(other, bitarray):
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

    #@profile
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

    def split(self, bitindex):
        return self[:bitindex], self[bitindex:]

    def _easy_mergable(self, other):
        return isinstance(other, NoCareBitarray) or\
            (isinstance(other, PreferFalseBitarray) and\
             self._val is False) or\
            (isinstance(other, ConstantBitarray) and\
                 other._val == self._val)

    def byteiter(self):
        if self._val:
            for _ in range(math.ceil(len(self)/8)):
                yield 0xFF
        else:
            for _ in range(math.ceil(len(self)/8)):
                yield 0

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
                return None#False
            raise IndexError("%s index out of range"%type(self))
        raise TypeError("%s indices must be integers or slices, not %s"%
                        (type(self), type(index)))

    def __iter__(self):
        for _ in range(self._length):
            yield None#False

    def __reversed__(self):
        for _ in range(self._length):
            yield None#False

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
            return ConstantBitarray(other._val,
                                    self._length+other._length)
        if isinstance(other, (bitarray, PreferFalseBitarray)):
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
            return ConstantBitarray(other._val,
                                    self._length+other._length)
        if isinstance(other, (bitarray, PreferFalseBitarray)):
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

    #@profile
    def tobytes(self):
        if not len(self):
            return b''
        return bytes([0x00]*(math.ceil(len(self)/8)))

    def reverse(self):
        pass

    def split(self, bitindex):
        return self[:bitindex], self[bitindex:]

    def _easy_mergable(self, other):
        return isinstance(other, (NoCareBitarray, PreferFalseBitarray,
                                  ConstantBitarray))

    def byteiter(self):
        for _ in range(math.ceil(len(self)/8)):
            yield 0

class PreferFalseBitarray(collections.Sequence):
    def __init__(self, length):
        self._length = length

    def __len__(self):
        return self._length
    def __getitem__(self, index):
        #import ipdb
        #ipdb.set_trace()
        if isinstance(index, slice):
            indices = index.indices(len(self))
            return PreferFalseBitarray(len(range(*indices)))

        if isinstance(index, int):
            index = len(self)-abs(index) if index < 0 else index
            if (index < self._length and index >= 0):
                return None#False
            raise IndexError("%s index out of range"%type(self))
        raise TypeError("%s indices must be integers or slices, not %s"%
                        (type(self), type(index)))

    def __iter__(self):
        for _ in range(self._length):
            yield None#False

    def __reversed__(self):
        for _ in range(self._length):
            yield None#False

    def __repr__(self):
        return "<F*: (%s)>"%self._length # pragma: no cover

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

        if isinstance(other, (PreferFalseBitarray, NoCareBitarray)):
            return PreferFalseBitarray(self._length+other._length)
        if isinstance(other, ConstantBitarray):
            if not other._val:
                return ConstantBitarray(False, self._length+other._length)
            return CompositeBitarray(self, other)
        if isinstance(other, bitarray):
            return CompositeBitarray(self, other)
        return NotImplemented

    def __radd__(self, other):
        if isinstance(other, bool):
            return NotImplemented
        if len(self) == 0:
            return other
        if len(other) == 0:
            return self

        if isinstance(other, (PreferFalseBitarray, NoCareBitarray)):
            return PreferFalseBitarray(self._length+other._length)
        if isinstance(other, ConstantBitarray):
            if not other._val:
                return ConstantBitarray(False, self._length+other._length)
            return CompositeBitarray(other, self)
        if isinstance(other, bitarray):
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

    #@profile
    def tobytes(self):
        if not len(self):
            return b''
        return bytes([0x00]*(math.ceil(len(self)/8)))

    def reverse(self):
        pass

    def split(self, bitindex):
        return self[:bitindex], self[bitindex:]

    def _easy_mergable(self, other):
        return isinstance(other, (NoCareBitarray, PreferFalseBitarray))\
            or (isinstance(other, ConstantBitarray) and\
                other._val is False)

    def byteiter(self):
        for _ in range(math.ceil(len(self)/8)):
            yield 0



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
                 *, offset=0, _tailoffset=0):
        """Create a bitarray object that stores its components by reference).

        Args:
            *components: Any number of bitarray instances to store in this composition.
        """
        #if component1 is None and component2 is None:
        #    raise ValueError("At least one component required")
        if component1 is None and component2 is not None:
            component1 = component2
            component2 = None

        self._llhead = None
        self._lltail = None
        self._length = 0
        self._offset = offset

        if isinstance(component1, CompositeBitarray):
            self._tailbitsused = len(component1._lltail.value)-_tailoffset
            self._length += len(component1)-self._offset-\
                            (len(component1._lltail.value)-\
                             self._tailbitsused)
            if self._offset == len(component1._llhead.value):
                self._llhead = component1._llhead.next
            else:
                self._llhead = component1._llhead
            self._lltail = component1._lltail
            self._offset += component1._offset
            #TODO Do something with the tailbitsused
        elif isinstance(component1, _DLLNode):
            self._tailbitsused = len(component1.value)-_tailoffset
            self._llhead = component1
            self._lltail = component1
            self._length += self._tailbitsused
            if self._offset + self._tailbitsused > len(component1.value):
                raise Exception("Invalid offset and tailbitsused")
            if component2 is not None:
                raise Exception("A CompositeBitarray created with a "
                                "_DLLNode can not currently have a "
                                "2nd component")
        else:
            self._tailbitsused = len(component1)-_tailoffset
            self._length += self._tailbitsused
            self._llhead = _DLLNode(component1)
            self._lltail = self._llhead

        if component2 is not None:
            oldtail = self._lltail
            if isinstance(component2, CompositeBitarray):
                if self._lltail is component2._llhead:
                    if  component1._tailbitsused != component2._offset:
                        raise ProteusDataJoinError()
                    self._lltail = component2._lltail
                    self._tailbitsused = component2._tailbitsused
                    self._length = len(component1)+len(component2)
                elif self._lltail.next is component2._llhead and\
                         self._tailoffset == 0 and\
                         component2._offset == 0:
                    self._length += len(component2)
                    self._lltail = component2._lltail
                    self._tailbitsused = component2._tailbitsused
                elif component2._llhead.prev is not None or\
                     self._llhead is component2._lltail:
                    #Will not catch everything. Good enough to
                    #prevent most accidents. A 'perfect' version
                    #would require walking the whole tree. No way.
                    raise ProteusDataJoinError()
                else:
                    self._length += len(component2)
                    self._lltail.next = component2._llhead
                    self._lltail = component2._lltail
                    self._tailbitsused = component2._tailbitsused
            else:
                if self._tailbitsused != self._taillen or\
                   self._lltail.next is not None:
                    raise ProteusDataJoinError()
                self._tailbitsused = len(component2)
                self._length += self._tailbitsused
                node = _DLLNode(component2)
                node.prev = self._lltail
                self._lltail = node

            #WHEN IT IS OK TO MERGE
            #oldtail can merge right if (oldtail is not head or offset is 0) and (oldtail.next is not tail or tailbitsused is len of node) and data is combinable. Do it recursive?
            #Merging can happen right until can't. Move back node and merge until can't. Repeat till new left node is incompatible.
            #if merging with the tail node, the tail node is fully used
            #Merge will start at seam, or have nothing to do.
            if oldtail is not self._llhead or self._offset == 0:
                self._do_merge(oldtail)

    def _do_merge(self, startpoint=None, stoponfail=True):
        headend = self._llhead if self._offset == 0 else \
                  self._llhead.next
        tailend = self._lltail if self._tailbitsused ==\
                  self._taillen else self._lltail.prev
        if not startpoint:
            startpoint = tailend.prev

        if headend is tailend:
            return #Skip if only one node in merge list.
        for mergebase in startpoint.iterprevtill(headend):
            anymerges = False
            mergetarget = mergebase.next
            while True:
                if mergebase.value._easy_mergable(mergetarget.value):
                    #Merge two links in the chain
                    anymerges = True
                    mergebase._value += mergetarget.value
                    mergebase.next = mergetarget.next
                    if mergetarget is self._lltail:
                        self._lltail = mergebase
                        self._tailbitsused = len(mergebase._value)
                else:
                    break

                if mergetarget is tailend:
                    tailend = mergebase
                    break
                mergetarget = mergetarget.next

            if not anymerges and stoponfail:
                break


    def _iter_components(self):
        for elem in self._llhead.iternexttill(self._lltail):
            yield elem.value

    def __len__(self):
        return self._length

    def __getitem__(self, index):
        if isinstance(index, int):
            print("GETTING", index, "WARNING, SLOW!")
            index = len(self)-abs(index) if index < 0 else index
            if (index < self._length and index >= 0):
                index += self._offset
                for elem in self._iter_components():
                    if index < len(elem):
                        return elem[index]
                    index -= len(elem)
                raise IndexError("Iteration finished before index found.")
            raise IndexError("%s index out of range"%type(self))

        raise TypeError("%s indices must be int, not %s"%
                        (type(self), type(index))
        )
    def __str__(self):
        return "".join(['?' if isinstance(elem, NoCareBitarray) else
                        ('!' if isinstance(elem, PreferFalseBitarray) else
                        (('T' if b else 'F') if isinstance(elem,
                                                    ConstantBitarray)
                         else ('1' if b else '0')))
                        for elem in self._iter_components()
                        for b in elem])\
                            [self._offset:-self._tailoffset or None]

    def __repr__(self):
        return "<CMP: %s (%s)>"%\
            (str(self), self._length)# pragma: no cover

    #@profile
    def __add__(self, other):
        if isinstance(other, (CompositeBitarray, ConstantBitarray,
                              NoCareBitarray, bitarray,
                              PreferFalseBitarray)):
            return CompositeBitarray(self, other)
        return NotImplemented
    #@profile
    def __radd__(self, other):
        if isinstance(other, (ConstantBitarray, NoCareBitarray,
                              bitarray, PreferFalseBitarray)):
            return CompositeBitarray(other, self)
        return NotImplemented

    def __iter__(self):
        node = self._llhead
        if self._llhead is self._lltail:
            for bit in islice(node.value, self._offset,
                              self._offset+self._tailbitsused):
                yield bit
            return
        else:
            for bit in islice(node.value, self._offset, None):
                yield bit

        while True:
            node = node.next
            if node is self._lltail:
                break
            for bit in node.value:
                yield bit

        for bit in islice(node.value, None,
                          self._tailbitsused or None):
            yield bit

    def __reversed__(self):
        node = self._lltail
        ptiter = reversed(node.value)
        for _ in range(self._tailoffset):
            next(ptiter)
        if node is self._llhead:
            for _ in range(self._tailoffset,
                           len(node.value)-self._offset):
                yield next(ptiter)
            return
        else:
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

    def __eq__(self, other):
        if isinstance(other, collections.Iterable):
            if len(self) != len(other):
                return False
            i1 = iter(self)
            i2 = iter(other)
            def checkwithnone(a, b):
                if a is None or b is None:
                    return True
                return a == b

            return all(checkwithnone(next(i1), v) for v in i2)
        return NotImplemented

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

    def split(self, bitindex, *, debug=False):
        if bitindex < 0:
            raise ValueError("bitindex must be larger or equal to 0.")
        if bitindex > len(self):
            raise ValueError("bitindex larger than the array's size.")
        if bitindex == 0:
            return None, self
        if bitindex == len(self):
            return self, None

        bitoffset = 0
        bitindexoffset =  bitindex + self._offset
        print(" => ".join(str(elem) for elem in self._iter_components()))
        for comp in self._llhead.iternexttill(self._lltail):
            print(bitindexoffset,
                  range(bitoffset+
                        (self._offset if self._llhead is self._lltail
                         else 0), bitoffset+len(comp.value)))
            if bitindexoffset in range(
                    bitoffset+(self._offset if self._llhead\
                               is self._lltail else 0),
                    bitoffset+len(comp.value)):
                break
            else:
                bitoffset += len(comp.value)


        if debug:
            import ipdb
            ipdb.set_trace()
        elemindex = bitindexoffset-bitoffset
        left = CompositeBitarray(self)
        left._lltail = comp if elemindex else comp.prev
        left._offset = self._offset
        left._tailbitsused = \
            (elemindex if elemindex else\
             len(comp.prev.value))-\
             (self._offset if left._lltail is left._llhead else 0)
        left._length = bitindex


        right = CompositeBitarray(self)
        right._llhead = comp.next if elemindex == len(comp.value)\
                        else comp
        right._offset = 0 if elemindex == len(comp.value)\
                        else elemindex
        right._tailbitsused = self._tailbitsused
        right._length = len(self)-bitindex
        return left, right

    def prepare(self, *, primef, reqef):
        """Extract the composite array's data into a usable bitarray based on if NoCare bits should be rendered as True or False.

        This method does the heavy lifting of producing a bitarray
        that is more efficient for tdo bits when that optimization is
        available.

        KWArgs:
            primef: A contracts.Requirement capability of the associated primitive.
            reqef: A contracts.Requirement (generated from primitive compilation) describing the signal requirements of the data in this CompositeBitarray.

        Returns:
            A bitarray (CompositeBitarray, ConstantBitarray, etc) that
            is the combined result of all the composite bitarray's
            components. If this CompositeBitarray's backing linked
            list can be merged into a single node, that single node is
            returned. Otherwise, this CompositeBitarray is returned.

        """
        if not primef.satisfies(reqef):
            raise Exception("Compiler error. Requested effect can not be "
                            "satisfied by primitive capabilities")
        assertPreferFalse = reqef == ZERO or primef == ARBITRARY or\
                            (reqef == NOCARE and primef == ZERO)
        testBitarrayFalse = reqef==ZERO or\
                            (reqef==NOCARE and primef==ZERO)
        testBitarrayTrue = reqef==ONE or (reqef==NOCARE and primef==ONE)
        assert not (testBitarrayTrue and testBitarrayFalse)

        #print("DATA", self)
        #print("ORIG", ["%s(%s:%s)"%
        #       (type(elem.value).__name__,
        #        elem.value._val if isinstance(elem.value,
        #                                      ConstantBitarray)\
        #        else "_", len(elem.value))
        #       for elem in self._llhead.iternexttill(self._lltail)])

        #import ipdb
        #ipdb.set_trace()
        if self._offset or self._tailoffset:
            if self._lltail is self._llhead:
                if isinstance(self._llhead.value, (ConstantBitarray,
                                             NoCareBitarray,
                                             PreferFalseBitarray)):
                    oldnode = self._llhead
                    if self._offset == 0:
                        oldnode.prev = None
                    if self._tailoffset == 0:
                        oldnode.next = None
                    self._llhead = _DLLNode(
                        oldnode.value[self._offset:\
                                      self._offset+self._tailbitsused])
                    self._lltail = self._llhead
                    self._offset = 0
                    self._tailbitsused = self._taillen

                elif isinstance(self._llhead.value, bitarray):
                    if testBitarrayFalse or testBitarrayTrue:
                        oldnode = self._llhead
                        newval = oldnode.value[self._offset:
                                               self._offset+self._tailbitsused]
                        if testBitarrayFalse:
                            if not newval.any():
                                newval = ConstantBitarray(False, len(newval))
                            else:
                                raise Exception("bitarray in data contains a 1")
                        if testBitarrayTrue:
                            if newval.all():
                                newval = ConstantBitarray(True, len(newval))
                            else:
                                raise Exception("bitarray in data contains a 0")

                        self._llhead = _DLLNode(newval)
                        self._lltail = self._llhead
                        self._offset = 0
                        self._tailbitsused = self._taillen

            else: #IF HEAD IS NOT TAIL
                if self._offset:
                    if isinstance(self._llhead.value,
                                  (ConstantBitarray, NoCareBitarray,
                                   PreferFalseBitarray)):
                        oldhead = self._llhead
                        self._llhead = _DLLNode(
                            oldhead.value[self._offset:])
                        self._llhead.next = oldhead.next
                        oldhead.next = None
                        self._offset = 0
                    elif isinstance(self._llhead.value, bitarray):
                        oldhead = self._llhead
                        newval = oldhead.value[self._offset:]
                        if testBitarrayFalse:
                            if not newval.any():
                                newval = ConstantBitarray(False, len(newval))
                            else:
                                raise Exception("bitarray in data contains a 1")
                        if testBitarrayTrue:
                            if newval.all():
                                newval = ConstantBitarray(True, len(newval))
                            else:
                                raise Exception("bitarray in data contains a 0")

                        self._llhead = _DLLNode(newval)
                        self._llhead.next = oldhead.next
                        oldhead.next = None
                        self._offset = 0

                if self._tailoffset:
                    if isinstance(self._lltail.value,
                                  (ConstantBitarray, NoCareBitarray,
                                   PreferFalseBitarray)):
                        oldtail = self._lltail
                        self._lltail = _DLLNode(
                            oldtail.value[:self._tailbitsused])
                        self._lltail.prev = oldhead.prev
                        oldtail.prev = None
                        self._tailbitsused = self._taillen
                    elif isinstance(self._lltail.value, bitarray):
                        oldtail = self._lltail
                        newval = oldtail.value[:self._tailbitsused]
                        if testBitarrayFalse:
                            if not newval.any():
                                newval = ConstantBitarray(False, len(newval))
                            else:
                                raise Exception("bitarray in data contains a 1")
                        if testBitarrayTrue:
                            if newval.all():
                                newval = ConstantBitarray(True, len(newval))
                            else:
                                raise Exception("bitarray in data contains a 0")

                        self._lltail = _DLLNode(newval)
                        self._lltail.prev = oldtail.prev
                        oldtail.prev = None
                        self._tailbitsused = self._taillen


        for elem in self._llhead.iternexttill(self._lltail):
            if isinstance(elem.value, PreferFalseBitarray):
                if assertPreferFalse:
                    elem._value = ConstantBitarray(False, len(elem.value))
                else:
                    elem._value = NoCareBitarray(len(elem.value))
            if isinstance(elem.value, bitarray):
                if testBitarrayFalse:
                    if not elem.value.any():
                        elem.value = ConstantBitarray(False,
                                                      len(elem.value))
                    else:
                        raise Exception("bitarray in data contains a 1")
                if testBitarrayTrue:
                    if elem.value.all():
                        elem.value = ConstantBitarray(True,
                                                      len(elem.value))
                    else:
                        raise Exception("bitarray in data contains a 0")


        #print("TRAN", ["%s(%s:%s)"%
        #       (type(elem.value).__name__,
        #        elem.value._val if isinstance(elem.value,
        #                                      ConstantBitarray)\
        #        else "_", len(elem.value))
        #       for elem in self._llhead.iternexttill(self._lltail)])



        if self._lltail is not self._llhead and\
           (self._lltail.next is not self._llhead or\
            (self._offset == 0 and self._tailbitsused == self._taillen)
            ):
            self._do_merge(stoponfail=False)

        #print("\033[1mPOST", "+ ".join(["%s%s(%s:%s)\033[0m"%
        #       ('\033[91m' if isinstance(elem.value, bitarray) else
        #        ('\033[94m' if isinstance(elem.value,
        #                            (NoCareBitarray, PreferFalseBitarray))
        #         else '\033[92m'),type(elem.value).__name__,
        #        elem.value._val if isinstance(elem.value,
        #                                      ConstantBitarray)\
        #        else (elem.value.to01() if isinstance(elem.value,
        #                                              bitarray)
        #              else "_"), len(elem.value))
        #       for elem in self._llhead.iternexttill(self._lltail)]))
        if self._lltail is self._llhead and self._offset == 0 and\
           self._tailbitsused == self._taillen:
            if isinstance(self._llhead.value, (NoCareBitarray,
                                               PreferFalseBitarray)):
                return ConstantBitarray(False, len(self._llhead.value))
            return self._llhead.value
        return self

    @property
    def _taillen(self):
        return len(self._lltail.value)

    @property
    def _tailoffset(self):
        return self._taillen-self._tailbitsused-\
            (self._offset if self._llhead is self._lltail else 0)

    def tobytes(self):
        def bnext(iterator):
            return bool(next(iterator))
        data = bytearray(math.ceil(len(self)/8))
        it = iter(self)
        i = -1
        for i in range((len(self)//8)//2):
            data[i<<1], data[(i<<1)+1] = \
                bitarray((bnext(it), bnext(it), bnext(it), bnext(it),
                          bnext(it), bnext(it), bnext(it), bnext(it),
                          bnext(it), bnext(it), bnext(it), bnext(it),
                          bnext(it), bnext(it), bnext(it), bnext(it)))\
                          .tobytes()
        i2 = (i+1)<<1

        if (len(self)/8)%2 >= 1:
            data[i2] =\
                (bnext(it)<<7 | bnext(it)<<6 | bnext(it)<<5 | bnext(it)<<4 |\
                 bnext(it)<<3 | bnext(it)<<2 | bnext(it)<<1 | bnext(it))
            i2 += 1

        offset = 7
        tmp = 0
        for b in it:
            tmp |= bool(b)<<offset
            offset -= 1
        data[-1] = tmp
        return data
        #tmpba = bitarray(self)
        #return tmpba.tobytes()

    def byteiter(self):
        #import ipdb
        #ipdb.set_trace()
        offset = 0
        res = 0
        for elem in self._iter_components():
            ielem = elem.byteiter()
            if offset == 0:
                for _ in range(len(elem)//8):
                    yield next(ielem)
                offset = len(elem)%8
                if offset:
                    res = next(ielem)&(0x100-(1<<(8-offset)))
            else:
                if len(elem) < 8-offset:
                    tmp2 = next(ielem)&(0x100-(1<<(8-len(elem))))
                    res |= tmp2 >> offset
                    offset += len(elem)
                elif len(elem) == 8-offset:
                    res |= next(ielem) >> offset
                    offset = 0
                    yield res
                else:
                    offsetinv = 8-offset
                    for _ in range((offset+len(elem))//8):
                        tmp2 = next(ielem)
                        yield (res | (tmp2>>offset))&0xFF
                        res = tmp2 << offsetinv

                    if (offset+len(elem))%8 == 0:
                        #If offset plus number of bits is divisible by 8.
                        #ONLY HAPPENS WHEN LAST BYTE PERFECTLY LINED UP
                        offset = 0
                    elif (offset+len(elem))%8 > offset:
                        #NEED MORE BITS
                        res |= next(ielem) >> offset
                        offset = (offset+len(elem))%8
                        res &= (0x100-(1<<(8-offset)))
                    else:
                        #NO MORE BITS NEEDED FOR CURRENT BYTE
                        res |= tmp2 >> offset
                        offset = (offset+len(elem))%8
                        res &= (0x100-(1<<(8-offset)))

        if offset:
            yield res

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
        if node is not None:
            node._prev = self

    @property
    def prev(self):
        return self._prev
    @prev.setter
    def prev(self, node):
        if self is node:
            raise ValueError("Invalid prev node. Infinite Loop")
        self._prev = node
        if node is not None:
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
