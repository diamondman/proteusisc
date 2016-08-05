import collections

from .jtagStateMachine import JTAGStateMachine
from .primative import Level1Primative, Level2Primative,\
    Level3Primative, Executable,\
    DOESNOTMATTER, ZERO, ONE, CONSTANT, SEQUENCE,\
    DefaultRunInstructionPrimative,\
    DeviceTarget

styles = {0:'\033[92m', #GREEN
          1:'\033[93m', #YELLOW
          2:'\033[91m'} #RED

class CommandQueue(object):
    def __init__(self, sc):
        self.queue = []
        self._fsm = JTAGStateMachine()
        self.sc = sc
        self._return_queue = []

    def flatten_macro(self, item):
        if not item._is_macro:
            return [item]
        else:
            queue = []
            for subitem in item._expand_macro(self):
                queue += self.flatten_macro(subitem)
            return queue

    def append(self, prim):
        self.queue.append(prim)
        #for item in self.flatten_macro(prim):
        #    if item._stage(self._fsm.state):
        #        if not item._staged:
        #            raise Exception("Primative not marked as staged after calling _stage.")
        #
        #        commit_res = item._commit(self)
        #        if isinstance(item, Executable):
        #            self.queue.append(item)
        #        else:
        #            #print("Need to render down", item)
        #            possible_prims = []
        #            reqef = item.required_effect
        #
        #            #print(('  \033[95m%s %s %s\033[94m'%tuple(reqef)).replace('0', '-'), item,'\033[0m')
        #            for p1 in self.sc._lv1_primatives:
        #                ef = p1._effect
        #                efstyledstr = ''
        #                worststyle = 0
        #                for i in range(3):
        #                    if reqef[i] is None:
        #                        reqef[i] = 0
        #
        #                    curstyle = 0
        #                    if (ef[i]&reqef[i]) is not reqef[i]:
        #                        curstyle = 1 if ef[i]==CONSTANT else 2
        #
        #                    #efstyledstr += "%s%s "%(styles.get(curstyle), ef[i])
        #                    if curstyle > worststyle:
        #                        worststyle = curstyle
        #
        #                if worststyle == 0:
        #                    possible_prims.append(p1)
        #                #print(" ",efstyledstr, styles.get(worststyle)+p1.__name__+"\033[0m")
        #
        #            if not len(possible_prims):
        #                raise Exception('Unable to match Primative to lower level Primative.')
        #            best_prim = possible_prims[0]
        #            for prim in possible_prims[1:]:
        #                if sum(prim._effect)<sum(best_prim._effect):
        #                    best_prim = prim
        #            #print("    POSSIBILITIES:", [p.__name__ for p in possible_prims])
        #            #print("    WINNER:", best_prim.__name__)
        #            bits = item.get_effect_bits()
        #            self.queue.append(best_prim(*bits))
        #
        #        if not item._committed:
        #            raise Exception("Primative not marked as committed after calling _commit.")
        #        if commit_res:
        #            self.flush()

    def reset(self):
        self._fsm.reset()
        self.queue = []

    def flush(self):
        #print("FLUSHING", self.queue)
        #for p in self.queue:
        #    if not isinstance(p, Executable):
        #        print("Need to render down", p)
        self.sc._controller.execute(self.queue)
        self.queue = []

    def get_return(self):
        res = self._return_queue
        self._return_queue = []
        if len(res)==1:
            return res[0]
        elif len(res)>1:
            return res
        return None

    def snapshot(self):
        return [p.snapshot() for p in self.queue]


class FrameSequence(collections.MutableSequence):
    def __init__(self, chain, *init_prims_lists):
        self._chain = chain
        self._frames = []
        self._frame_types = []
        for p in init_prims_lists[0]:
            self._frame_types.append(p._group_type)
            self._frames.append(Frame(self._chain, p))
        for ps in init_prims_lists[1:]:
            self.addstream(ps)

    def __len__(self):
        return len(self._frames)

    def __delitem__(self, index):
        self._frames.__delitem__(index)

    def insert(self, index, value):
        self._frames.insert(index, value)

    def __setitem__(self, index, value):
        self._frames.__setitem__(index, value)

    def __getitem__(self, index):
        return self._frames.__getitem__(index)

    #def __repr__(self):
    #    return "<Frame%s>"%self._frames

    #Needleman–Wunsch algorithm
    def _lcs(self, prims):
        lengths = [[0 for j in range(len(prims)+1)]
                   for i in range(len(self._frame_types)+1)]
        # row 0 and column 0 are initialized to 0 already
        for i, x in enumerate(self._frame_types):
            for j, y in enumerate([x._group_type for x in prims]):
                if x == y:
                    lengths[i+1][j+1] = lengths[i][j] + 1
                else:
                    lengths[i+1][j+1] = max(lengths[i+1][j], lengths[i][j+1])
        result = []
        x, y = len(self._frame_types), len(prims)
        while x != 0 and y != 0:
            if lengths[x][y] == lengths[x-1][y]:
                x -= 1
            elif lengths[x][y] == lengths[x][y-1]:
                y -= 1
            else:
                result = [self._frame_types[x-1]] + result
                x -= 1
                y -= 1
        return result

    def finalize(self):
        for f in self._frames:
            f.fill()
        return self

    def addstream(self, prims):
        i1, i2, selfoffset = 0, 0, 0
        for c in self._lcs(prims):
            while True:
                if self._frame_types[i1] == prims[i2]._group_type == c:
                    self._frames[i1].add(prims[i2])
                    i1 += 1
                    i2 += 1
                    break
                elif self._frame_types[i1] == c: #s2 does not match.
                    self.insert(i1+selfoffset,
                                Frame.from_prim(self._chain,prims[i2]))
                    i2 += 1
                    selfoffset += 1
                elif prims[i2]._group_type == c: #s1 does not match.
                    i1 += 1
                else: #NEITHER IN SEQUENCE
                    i1 += 1
                    self.insert(i1+selfoffset,
                                Frame.from_prim(self._chain,prims[i2]))
                    i2 += 1
                    selfoffset += 1

        for p in prims[i2:]:
            self.append(Frame.from_prim(self._chain, p))

        return self

    def insert(self, index, val):
        self._frames.insert(index, val)
        self._frame_types.insert(index, val._group_type)

    def snapshot(self):
        tracks = [[] for i in range(len(self._chain._devices))]
        for frame in self:
            if frame._dev_specific:
                for p in frame:
                    tracks[p._device_index].append(p.snapshot())
            else:
                tracks[0].append(frame[0].snapshot())
                for i, p in enumerate(frame[1:]):
                    tracks[i+1].append({'valid':False})

        return tracks


class Frame(collections.MutableSequence):
    def __init__(self, chain, *prims, autofill=False):
        self._chain = chain
        self._inner_list = [None for i in range(len(chain._devices))]
        self._valid_prim = None
        self._layer = None
        self._dev_specific = True
        if prims:
            self.add(*prims)
        if autofill:
            self.fill()

    def add(self, *args):
        for prim in args:
            if not self._valid_prim:
                self._valid_prim = prim
                self._layer = type(prim)._layer
                self._dev_specific = isinstance(prim, DeviceTarget)
                if self._dev_specific:
                    self[prim._device_index] = prim
                else:
                    self[0] = prim
                    #self._inner_list = [prim]
            elif not self._dev_specific:
                raise ValueError("Only one non device specific prim "
                                 "allowed in a Frame at once.")
            elif self._valid_prim._group_type == prim._group_type\
                 and type(self._valid_prim) == type(prim):
                self[prim._device_index] = prim
            else:
                raise ValueError("Incompatible primitives")

    def fill(self):
        if not self._valid_prim:
            raise ValueError("No valid primitives inserted before fill called")
        if self._dev_specific:
            for i, p in enumerate(self):
                if p is None:
                    self[i] = self._valid_prim.get_placeholder_for_dev(
                        self._chain._devices[i])

    @property
    def _group_type(self):
        return self._valid_prim._group_type

    def __len__(self):
        return len(self._inner_list)

    def __delitem__(self, index):
        self._inner_list.__delitem__(index)

    def insert(self, index, value):
        self._inner_list.insert(index, value)

    def __setitem__(self, index, value):
        self._inner_list.__setitem__(index, value)

    def __getitem__(self, index):
        return self._inner_list.__getitem__(index)

    def __repr__(self):
        return "<Frame%s>"%self._inner_list

    @classmethod
    def from_prim(cls, chain, *prim):
        return cls(chain, *prim, autofill=True)
