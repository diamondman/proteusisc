class TDOPromise(object):
    count = 0
    def __init__(self, chain):
        self.sn = TDOPromise.count
        TDOPromise.count += 1
        self._chain = chain
        self._value = None

    def __call__(self):
        if self._value:
            return self._value
        self._chain.flush()
        return self._value

    def __repr__(self):
        return "<P %s>"%self.sn
