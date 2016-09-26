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
            if (index < self._length and index >= 0) or\
               (self._length and index == -1):
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
    def __init__(self, length):
        self._length = length

    def __len__(self):
        return self._length
    def __getitem__(self, index):
        if isinstance(index, slice):
            indices = index.indices(len(self))
            return NoCareBitarray(len(range(*indices)))

        if isinstance(index, int):

            if (index < self._length and index >= 0) or\
               (self._length and index == -1):
                return False
            raise IndexError("%s index out of range"%type(self))
        raise TypeError("%s indices must be integers or slices, not %s"%
                        (type(self), type(index)))
    def __repr__(self):
        return "<NC: (%s)>"%(self._length) # pragma: no cover
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
        if isinstance(other, ConstantBitarray):
            return ConstantBitarray(other._val,
                                    self._length+other._length)
        if isinstance(other, bool):
            return ConstantBitarray(other, self._length+1)
        if isinstance(other, bitarray):
            return bitarray(self)+other
        return NotImplemented
    def __radd__(self, other):
        if isinstance(other, ConstantBitarray):
            return ConstantBitarray(other._val,
                                    self._length+other._length)
        if isinstance(other, bool):
            return ConstantBitarray(other, self._length+1)
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
