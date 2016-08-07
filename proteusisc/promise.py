class TDOPromise(object):
    def __init__(self, chain):
        self._chain = chain
        self._value = None

    def __call__(self):
        if self._value:
            return self._value
        self._chain.flush()
        return self._value
