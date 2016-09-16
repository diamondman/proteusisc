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
        return "<P %s; bit %s; len %s>" % (self.sn, self._bitstart,
                                           self._bitlength)

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
                self._value = bits
            else:
                self._value = self._components[0][0]._value
                for sub, offset in self._components[1:]:
                    self._value += sub._value
            if self._parent is not None:
                parent = self._parent
                parent._fulfill(bits[parent._bitstart:parent._bitend])

    def _allsubsfulfilled(self):
        for sub, offset in self._components:
            if sub._value is None:
                return False
        return True

class TDOPromiseCollection(object):
    def __init__(self, chain, bitlength):
        self._bitlength = bitlength
        self._promises = []
        self.sn = TDOPromise.count
        self._chain = chain
        TDOPromise.count += 1

    def add(self, promise, bitoffset):
        #Assuming that things are added in order.
        #Sorting or checking should likely be added.
        if isinstance(promise, TDOPromise):
            if bitoffset is 0:
                newpromise = promise
            else:
                newpromise = TDOPromise(promise._chain,
                                        promise._bitstart + bitoffset,
                                        promise._bitlength,
                                        _parent=promise)
                promise._addsub(newpromise, 0)
            self._promises.append(newpromise)
        elif isinstance(promise, TDOPromiseCollection):
            for p in promise._promises:
                self.add(p, bitoffset)

    def split_to_subpromises(self):
        if self._bitlength in (0,1):
            return None, self
        if len(self._promises) is 0:
            return self, None
        endbits = 1
        bitnum = self._bitlength-endbits

        p = self._promises[-1]
        if p._bitstart <= bitnum and p._bitend >= bitnum:
            rest, tail = p.split_to_subpromises()
            real_rest = TDOPromiseCollection(self._chain,
                                             self._bitlength-1)
            real_rest._promises = self._promises[:-1]+([rest] \
                                                if rest else [])
            return real_rest, tail
        else:
            #DO NOTHING
            return self, None

    def __repr__(self):
        return "<PC %s; %s>" % (self.sn, self._promises)

    def __bool__(self):
        return bool(self._promises)

    def _fulfill(self, bits):
        for promise in reversed(self._promises):
            promise._fulfill(bits[promise._bitstart:promise._bitend])
