import collections

from .jtagStateMachine import JTAGStateMachine
from .primative import Level1Primative, Level2Primative,\
    Level3Primative, Executable, DeviceTarget,\
    DOESNOTMATTER, ZERO, ONE, CONSTANT, SEQUENCE
from .primative_defaults import DefaultRunInstructionPrimative

class CommandQueue(collections.MutableSequence):
    def __init__(self, sc):
        self.queue = []
        self._fsm = JTAGStateMachine()
        self.sc = sc
        self._return_queue = []

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

    def insert(self, index, val):
        self.queue.insert(index, val)
