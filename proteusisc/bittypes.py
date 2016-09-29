import collections
from bitarray import bitarray

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
        if isinstance(other, ConstantBitarray):
            if self._val == other._val:
                return ConstantBitarray(self._val,
                                        self._length+other._length)
            else:
                return bitarray((*(self._val,)*self._length,
                                 *(other._val,)*other._length))
        if isinstance(other, bool):
            if self._val == other:
                return ConstantBitarray(self._val, self._length+1)
            else:
                return bitarray((*(self._val,)*self._length, other))
        if isinstance(other, bitarray):
            return bitarray(self)+other
        return NotImplemented
    def __radd__(self, other):
        if isinstance(other, bool):
            if self._val == other:
                return ConstantBitarray(self._val, self._length+1)
            else:
                return bitarray((other, *(self._val,)*self._length))
        return NotImplemented

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
    def __init__(self, length, *, _preserve=False):
        self._length = length
        self._preserve = _preserve

    def __len__(self):
        return self._length
    def __getitem__(self, index):
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
    def __repr__(self):
        return "<NC%s: (%s)>"%("(P)" if self._preserve else "",
                               self._length) # pragma: no cover
    def __add__(self, other):
        """Handles combining different bitarray types.

        There are special rules for combining each type of bitarray:
        bitarray, ConstantBitarray, and NoCareBitArray. For example,
        two NoCareBitarrays combine into a bigger NoCareBit array,
        while combining two ConstantBitArrays depends on if the two
        array's constant value are the same.
        """
        if isinstance(other, NoCareBitarray):
                return NoCareBitarray(self._length+other._length)

        if self._preserve:
            if isinstance(other, (CompositeBitarray, ConstantBitarray,
                                  bitarray)):
                return CompositeBitarray(self, other)
            if isinstance(other, bool):
                return CompositeBitarray(self, ConstantBitarray(other, 1))
        else:
            if isinstance(other, ConstantBitarray):
                return ConstantBitarray(other._val, len(self)+len(other))
            if isinstance(other, bool):
                return ConstantBitarray(other, len(self)+1)
            if isinstance(other, bitarray):
                return bitarray(self)+other
        return NotImplemented
    def __radd__(self, other):
        if self._preserve:
            if isinstance(other, (CompositeBitarray, ConstantBitarray)):
                return CompositeBitarray(other, self)
            if isinstance(other, bool):
                return CompositeBitarray(ConstantBitarray(other, 1), self)
        else:
            if isinstance(other, ConstantBitarray):
                return ConstantBitarray(other._val, len(self)+len(other))
            if isinstance(other, bool):
                return ConstantBitarray(other, len(self)+1)
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
    #TODO add iterator to speed up walking structure
    def __init__(self, *components):
        """Create a bitarray object that stores its components by reference).

        Args:
            *components: Any number of bitarray instances to store in this composition.
        """
        #TODO Check if this lookup structure causes slowdown.
        self._components = []
        self._length = 0
        for elem in components:
            if isinstance(elem, CompositeBitarray):
                for subelem in elem._components:
                    self._add_elem(subelem[1])
            else:
                self._add_elem(elem)

    def _add_elem(self, elem):
        self._components.append(
            (range(self._length, self._length+len(elem)), elem))
        self._length += len(elem)

    def _lookup_range(self, index):
        for r, elem in self._components:
            if index in r:
                return r, elem
        return None, None #pragma: no cover

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
        #if isinstance(index, slice):
        #    indices = index.indices(len(self))
        #    return ConstantBitarray(self._val, len(range(*indices)))
        if isinstance(index, int):
            index = len(self)-abs(index) if index < 0 else index
            print(index)
            if (index < self._length and index >= 0):
                r, elem = self._lookup_range(index)
                return elem[index-r.start]
            raise IndexError("%s index out of range"%type(self))
        raise TypeError("%s indices must be integers, not %s"%
                        (type(self), type(index)))
    def __repr__(self):
        return "<CMP: %s (%s)>"%\
            ("".join(['?' if isinstance(elem[1], NoCareBitarray) else
                      (('T' if b else 'F') if isinstance(elem[1],
                                                         ConstantBitarray)
                       else ('1' if b else '0'))
                      for elem in self._components for b in elem[1]]),
             self._length)# pragma: no cover
    def __add__(self, other):
        if isinstance(other, (CompositeBitarray, ConstantBitarray)):
            return CompositeBitarray(self, other)
        return NotImplemented
    def __radd__(self, other):
        if isinstance(other, (CompositeBitarray, ConstantBitarray)):
            return CompositeBitarray(other, self)
        return NotImplemented

    def count(self, val=True):
        """Get the number of bits in the array with the specified value.

        Args:
            val: A boolean value to check against the array's value.

        Returns:
            An integer of the number of bits in the array equal to val.
        """
        count = 0
        for r, elem in self._components:
            print(elem, val, elem.count(val))
            count += elem.count(val)
        return count

    def any(self):
        for r, elem in self._components:
            if elem.any():
                return True
        return False

    def all(self):
        for r, elem in self._components:
            if not elem.all():
                return False
        return True

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
        for r, elem in self._components:
            if isinstance(elem, NoCareBitarray):
                if elem._preserve:
                    if preserve_history:
                        res += ConstantBitarray(False, len(elem))
                    else:
                        res += NoCareBitarray(len(elem))
                else:
                    res += elem
            else:
                res += elem
        return res
