class TDOPromise(object):
    """Placeholder/Container for a value that isn't available immediately.

    When a primitive is created and asked to return a value, a promise
    is returned instead of the requested value. This delayed
    satisfaction of return values allows for more aggressive
    optimizations of the primitive stream.

    Promises track a return value from a primitive. As the primitive
    is modified, split, and joined with other primitives during the
    compilation process, the ultimate source of the data to fulfill
    the promise changes. The promise tracks the data about the
    transformation of its original primitives and can piece the
    appropriate bits together to form its value.

    Some primitives support arbitrary tdo bits. When a primitive that
    returns TDO and anoter one that does not are merged into a
    primitive that supports arbitrary TDO bits, the resulting
    primitive can specify exactly which bits it wants to be read back
    from the chip (This is tracked with the ComponentBitarray
    class). When this happend, normal offsets do not work anymore
    since they are based on the assumption that all bits are
    returned. A new offset must be tracked in case the final primitive
    supports arbitrary TDO.

    It does not seem that this new offset can replace the original
    offset, nor can No Care bits for tdo be rendered as False if the
    current primitive supports Arbitrary bits since it may be merged
    into another prim and end up unable to execute. Until a more
    elegant solution comes up, both offsets must be stored.

    A promise's value can be returned by calling the promise:
        res = mypromise()

    If a promise does not yet have a value, it will automatically
    trigger a flush operation on the associated JTAGScanChain, which
    will compile and execute all pending primitives and distribute the
    resulting data to the promises.

    Reading the value of any promise from the currently unexecuted set
    of primitives will automatically run all pending primitives, and
    fulfill all their promises.

    Manually flushing the scan chain will automatically fulfill all
    pending promises.


    Args:
        chain: A JTAGScanChain associated with this promise's primitie.
        bitstart: An integer offset used for selecting which bits of the original primitive the promise is selecting.
        bitlength: An integer count of how many bits of the original primitive should be selected by this promise.
        bitstartselective: The index to use if only the needed tdo bits are returned instead of all bits for a primitive.

    """
    count = 0
    def __init__(self, chain, bitstart, bitlength, *,
                 _parent=None, bitstartselective=None):
        self.sn = TDOPromise.count
        TDOPromise.count += 1
        self._chain = chain
        self._value = None
        self._parent = _parent
        self._components = []
        self._bitstart = bitstart
        self._bitlength = bitlength
        self._bitstartselective = bitstartselective if \
                                  bitstartselective is not None else\
                                  bitstart

    def __call__(self):
        if self._value:
            return self._value
        self._chain.flush()
        return self._value

    def __repr__(self):
        return "<P %s; bit %s; len %s; parent: %s; bitideal:%s>" %\
            (self.sn, self._bitstart, self._bitlength,
             self._parent.sn if self._parent else "NONE",
             self._bitstartselective)\
             #pragma: no cover

    def __len__(self):
        return self._bitlength

    @property
    def bitstart(self):
        return self._bitstart

    @property
    def bitlength(self):
        return self._bitlength

    @property
    def bitend(self):
        return self._bitend

    @property
    def _bitend(self):
        return self._bitstart + self._bitlength

    def _addsub(self, subpromise, offset):
        self._components.append((subpromise, offset))

    def split(self, bitindex):
        """Split a promise into two promises at the provided index.

        A common operation in JTAG is reading/writing to a
        register. During the operation, the TMS pin must be low, but
        during the writing of the last bit, the TMS pin must be
        high. Requiring all reads or writes to have full arbitrary
        control over the TMS pin is unrealistic.

        Splitting a promise into two sub promises is a way to mitigate
        this issue. The final read bit is its own subpromise that can
        be associated with a different primitive than the 'rest' of
        the subpromise.

        Returns:
            Two TDOPromise instances: the 'Rest' and the 'Tail'.
            The 'Rest' is the first chunk of the original promise.
            The 'Tail' is a single bit sub promise for the final bit
              in the operation

            If the 'Rest' would have a length of 0, None is returned

        """
        if bitindex < 0:
            raise ValueError("bitindex must be larger or equal to 0.")
        if bitindex > len(self):
            raise ValueError(
                "bitindex larger than the array's size. "
                "Len: %s; bitindex: %s"%(len(self), bitindex))

        if bitindex == 0:
            return None, self
        if bitindex == len(self):
            return self, None

        left = TDOPromise(self._chain, self._bitstart, bitindex,
                          _parent=self)
        #Starts at 0 because offset is for incoming data from
        #associated primitive, not location in parent.
        right = TDOPromise(self._chain, 0, len(self)-bitindex,
                          _parent=self)
        self._components = []
        self._addsub(left, 0)
        self._addsub(right, bitindex)
        return left, right

    def _fulfill(self, bits, ignore_nonpromised_bits=False):
        """Supply the promise with the bits from its associated primitive's execution.

        The fulfillment process must walk the promise chain backwards
        until it reaches the original promise and can supply the final
        value.

        The data that comes in can either be all a bit read for every
        bit written by the associated primitive, or (if the primitive
        supports it), only the bits that are used by promises. The
        ignore_nonpromised_bits flag specifies which format the
        incoming data is in.

        Args:
            bits: A bitarray (or compatible) containing the data read from the jtag controller's TDO pin.
            ignore_nonpromised_bits: A boolean specifying if only promised bits are being returned (and thus the 2nd index of the promise must be used for slicing the incoming data).

        """
        if self._allsubsfulfilled():
            if not self._components:
                if ignore_nonpromised_bits:
                    self._value = bits[self._bitstartselective:
                                       self._bitstartselective +
                                       self._bitlength]
                else:
                    self._value = bits[self._bitstart:self._bitend]
            else:
                self._value = self._components[0][0]._value
                for sub, offset in self._components[1:]:
                    self._value += sub._value
            if self._parent is not None:
                self._parent._fulfill(None)

    def _allsubsfulfilled(self):
        """Check if every subpromise has been fulfilles

        Returns:
            A boolean describing if all subpromises have been fulfilled
        """
        return not any((sub._value is None
                        for sub, offset in self._components))

    def makesubatoffset(self, bitoffset, *, _offsetideal=None):
        """Create a copy of this promise with an offset, and use it as this promise's child.

        If this promise's primitive is being merged with another
        primitive, a new subpromise may be required to keep track of
        the new offset of data coming from the new primitive.


        Args:
            bitoffset: An integer offset of the data in the new primitive.
        _offsetideal: integer offset of the data if terms of bits actually used for promises. Used to calculate the start index to read if the associated primitive has arbitrary TDO control.

        Returns:
            A TDOPromise registered with this promise, and with the
            correct offset.

        """
        if _offsetideal is None:
            _offsetideal = bitoffset
        if bitoffset is 0:
            return self
        newpromise = TDOPromise(
            self._chain,
            self._bitstart + bitoffset,
            self._bitlength,
            _parent=self,
            bitstartselective=self._bitstartselective+_offsetideal
        )
        self._addsub(newpromise, 0)
        return newpromise


class TDOPromiseCollection(object):
    """A collection of TDOPromises for primitives with multiple promises to fulfill can easily apply promise operations to all of them.

    Args:
        chain: A JTAGScanChain associated with this promise's primitie.
        bitlength: An integer count of how many bits of the original primitive should be selected by this promise.

    """
    def __init__(self, chain):
        self._promises = []
        self._chain = chain
        self.sn = TDOPromise.count
        TDOPromise.count += 1

    def add(self, promise, bitoffset, *, _offsetideal=None):
        """Add a promise to the promise collection at an optional offset.

        Args:
            promise: A TDOPromise to add to this collection.
            bitoffset: An integer offset for this new promise in the collection.
            _offsetideal: An integer offset for this new promise in the collection if the associated primitive supports arbitrary TDO control.
        """
        #This Assumes that things are added in order.
        #Sorting or checking should likely be added.
        if _offsetideal is None:
            _offsetideal = bitoffset
        if isinstance(promise, TDOPromise):
            newpromise = promise.makesubatoffset(
                bitoffset, _offsetideal=_offsetideal)
            self._promises.append(newpromise)
        elif isinstance(promise, TDOPromiseCollection):
            for p in promise._promises:
                self.add(p, bitoffset, _offsetideal=_offsetideal)

    def split(self, bitindex):
        """Split a promise into two promises. A tail bit, and the 'rest'.

        Same operation as the one on TDOPromise, except this works
        with a collection of promises and splits the appropriate one.

        Returns:
            The 'Rest' and the 'Tail'.
            The 'Rest' is TDOPromiseCollection containing the first
              chunk of the original TDOPromiseCollection.
            The 'Tail' is a single bit sub promise for the final bit
              in the operation

            If the 'Rest' would have a length of 0, None is returned

        """
        if bitindex < 0:
            raise ValueError("bitindex must be larger or equal to 0.")
        if bitindex == 0:
            return None, self

        lastend = 0
        split_promise = False
        for splitindex, p in enumerate(self._promises):
            if bitindex in range(lastend, p._bitstart):
                split_promise = False
                break
            if bitindex in range(p._bitstart, p._bitend):
                if bitindex-p._bitstart == 0:
                    split_promise = False
                else:
                    split_promise = True
                break
            lastend = p._bitend
        else:
            raise Exception("Should be impossible")

        processed_left = TDOPromiseCollection(self._chain)
        processed_right = TDOPromiseCollection(self._chain)

        if split_promise:
            left, right = p.split(bitindex-p._bitstart)

            for i in range(splitindex):
                processed_left.add(self._promises[i], 0)
            processed_left.add(left, 0)

            processed_right.add(right, 0)
            for tmpprim in self._promises[splitindex+1:]:
                processed_right.add(tmpprim, -bitindex)
            return processed_left, processed_right
        else:
            for i in range(splitindex):
                processed_left.add(self._promises[i], 0)

            for i in range(splitindex, len(self._promises)):
                processed_right.add(self._promises[i], -bitindex)

            return processed_left, processed_right

    def __repr__(self):
        return "<PC %s (%s bits); %s>" % (self.sn, len(self), self._promises) #pragma: no cover

    def __len__(self):
        return sum((len(p) for p in self._promises))

    def __bool__(self):
        return bool(self._promises)

    def _fulfill(self, bits, ignore_nonpromised_bits=False):
        for promise in self._promises:
            promise._fulfill(
                bits,
                ignore_nonpromised_bits=ignore_nonpromised_bits
            )

    def makesubatoffset(self, bitoffset, *, _offsetideal=None):
        """Create a copy of this PromiseCollection with an offset applied to each contained promise and register each with their parent.

        If this promise's primitive is being merged with another
        primitive, a new subpromise may be required to keep track of
        the new offset of data coming from the new primitive.

        Args:
            bitoffset: An integer offset of the data in the new primitive.
            _offsetideal: An integer offset to use if the associated primitive supports arbitrary TDO control.

        Returns:
            A new TDOPromiseCollection registered with this promise
            collection, and with the correct offset.

        """
        if _offsetideal is None:
            _offsetideal = bitoffset
        if bitoffset is 0:
            return self
        newpromise = TDOPromiseCollection(self._chain)
        for promise in self._promises:
            newpromise.add(promise, bitoffset, _offsetideal=_offsetideal)
        return newpromise
