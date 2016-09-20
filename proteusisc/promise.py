class TDOPromise(object):
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
        for sub, offset in self._components:
            if sub._value is None:
                return False
        return True

    def makesubatoffset(self, bitoffset):
        newpromise = TDOPromise(self._chain,
                                self._bitstart + bitoffset,
                                self._bitlength,
                                _parent=self)
        self._addsub(newpromise, 0)
        return newpromise


class TDOPromiseCollection(object):
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
        newpromise = TDOPromiseCollection(self._chain, self._bitlength)
        for promise in self._promises:
            newpromise.add(promise, bitoffset)
        return newpromise
