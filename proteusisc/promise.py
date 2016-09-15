class TDOPromise(object):
    count = 0
    def __init__(self, chain, bitstart, bitlength):
        self.sn = TDOPromise.count
        TDOPromise.count += 1
        self._chain = chain
        self._value = None
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

    def _addsub(self, subpromise):
        self._components.append(subpromise)

    def split_to_subpromises(self):
        if self._bitlength is 1:
            return None, self

        rest = TDOPromise(self._chain, self._bitstart, self._bitlength-1)
        tail = TDOPromise(self._chain, 0, 1)
                          #self._bitstart+self._bitlength-1, 1)
        self._components = []
        self._addsub(rest)
        self._addsub(tail)
        return rest, tail

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
                newpromise = TDOPromise(self._chain,
                                        promise._bitstart + bitoffset,
                                        promise._bitlength)
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
