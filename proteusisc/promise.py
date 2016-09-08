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

    def _addsub(self, subpromise):
        self._components.append(subpromise)
