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
    """
    count = 0
    def __init__(self, chain, bitstart, bitlength, *, _parent=None):
        self.sn = TDOPromise.count
        TDOPromise.count += 1
        self._chain = chain
        self._value = None
        self._parent = _parent
        self._components = []
        self._bitstart = bitstart
        self._bitlength = bitlength

    def __call__(self):
        if self._value:
            return self._value
        self._chain.flush()
        return self._value

    def __repr__(self):
        return "<P %s; bit %s; len %s; parent: %s>" %\
            (self.sn, self._bitstart, self._bitlength,
             self._parent.sn if self._parent else "NONE")\
             #pragma: no cover

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

    def split_to_subpromises(self):
        """Split a promise into two promises. A tail bit, and the 'rest'.

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
        if self._bitlength is 1:
            return None, self

        rest = TDOPromise(self._chain, self._bitstart, self._bitlength-1,
                          _parent=self)
        tail = TDOPromise(self._chain, 0, 1, _parent=self)
        self._components = []
        self._addsub(rest, 0)
        self._addsub(tail, self._bitlength-1)
        return rest, tail

    def _fulfill(self, bits):
        if self._allsubsfulfilled():
            if not self._components:
                self._value = bits[self._bitstart:self._bitend]
            else:
                components = self._components[::-1]
                self._value = components[0][0]._value
                for sub, offset in components[1:]:
                    self._value += sub._value
            if self._parent is not None:
                self._parent._fulfill(None)

    def _allsubsfulfilled(self):
        """Check if every subpromise has been fulfilles

        Returns:
            A boolean describing if all subpromises have been fulfilled
        """
        for sub, offset in self._components:
            if sub._value is None:
                return False
        return True

    def makesubatoffset(self, bitoffset):
        """Create a copy of this promise with an offset, and use it as this promise's child.

        If this promise's primitive is being merged with another
        primitive, a new subpromise may be required to keep track of
        the new offset of data coming from the new primitive.

        Args:
            bitoffset: An integer offset of the data in the new primitive.

        Returns:
            A TDOPromise registered with this promise, and with the
            correct offset.

        """
        if bitoffset is 0:
            return self
        newpromise = TDOPromise(self._chain,
                                self._bitstart + bitoffset,
                                self._bitlength,
                                _parent=self)
        self._addsub(newpromise, 0)
        return newpromise


class TDOPromiseCollection(object):
    """A collection of TDOPromises for primitives with multiple promises to fulfill can easily apply promise operations to all of them.

    Args:
        chain: A JTAGScanChain associated with this promise's primitie.
        bitlength: An integer count of how many bits of the original primitive should be selected by this promise.

    """
    def __init__(self, chain, bitlength):
        self._bitlength = bitlength
        self._promises = []
        self._chain = chain
        self.sn = TDOPromise.count
        TDOPromise.count += 1

    def add(self, promise, bitoffset):
        #This Assumes that things are added in order.
        #Sorting or checking should likely be added.
        if isinstance(promise, TDOPromise):
            if bitoffset is 0:
                newpromise = promise
            else:
                newpromise = promise.makesubatoffset(bitoffset)
            self._promises.append(newpromise)
        elif isinstance(promise, TDOPromiseCollection):
            for p in promise._promises:
                self.add(p, bitoffset)

    def split_to_subpromises(self):
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
        if self._bitlength in (0,1):
            return None, self
        if len(self._promises) is 0:
            return self, None
        p = self._promises[0]
        if p._bitstart <= 1 and p._bitend >= 1:
            rest, tail = p.split_to_subpromises()
            real_rest = TDOPromiseCollection(self._chain,
                                             self._bitlength-1)
            real_rest.add(rest, 0)
            for tmpprim in self._promises[1:]:
                real_rest.add(tmpprim, -1)
            return real_rest, tail
        else:
            #DO NOTHING
            return self, None

    def __repr__(self):
        return "<PC %s; %s>" % (self.sn, self._promises) #pragma: no cover

    def __bool__(self):
        return bool(self._promises)

    def _fulfill(self, bits):
        for promise in self._promises:
            promise._fulfill(bits)

    def makesubatoffset(self, bitoffset):
        """Create a copy of this PromiseCollection with an offset applied to each contained promise and register each with their parent.

        If this promise's primitive is being merged with another
        primitive, a new subpromise may be required to keep track of
        the new offset of data coming from the new primitive.

        Args:
            bitoffset: An integer offset of the data in the new primitive.

        Returns:
            A new TDOPromiseCollection registered with this promise
            collection, and with the correct offset.

        """
        if bitoffset is 0:
            return self
        newpromise = TDOPromiseCollection(self._chain, self._bitlength)
        for promise in self._promises:
            newpromise.add(promise, bitoffset)
        return newpromise
