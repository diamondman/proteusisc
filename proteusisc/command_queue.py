import collections

from .jtagStateMachine import JTAGStateMachine

class CommandQueue(collections.MutableSequence):
    def __init__(self, chain):
        self.queue = []
        self._fsm = JTAGStateMachine()
        self._chain = chain

    def reset(self):
        self._fsm.reset()
        self.queue = []

    def snapshot(self):
        return [p.snapshot() for p in self.queue]

    def __len__(self):
        return len(self.queue)

    def __delitem__(self, index):
        self.queue.__delitem__(index)

    def insert(self, index, value):
        self.queue.insert(index, value)

    def __setitem__(self, index, value):
        self.queue.__setitem__(index, value)

    def __getitem__(self, index):
        return self.queue.__getitem__(index)

    def append(self, elem):
        elem._chain = self._chain
        super(CommandQueue, self).append(elem)
