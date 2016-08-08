import collections
from .primitive import DeviceTarget, Primitive

class Frame(collections.MutableSequence):
    def __init__(self, chain, *prims, fill=False):
        self._chain = chain
        self._prims = [None for i in range(len(chain._devices))]
        self._valid_prim = None
        self._layer = None
        self._dev_specific = True
        if prims:
            self.add(*prims)
        if fill:
            self.fill()

    def add(self, *args: Primitive):
        for prim in args:
            if prim is None:
                raise ValueError("None is not a valid prom. "
                                 "Maybe you called add(*frame) "
                                 "for a frame that has non device "
                                 "specific prims.")
            elif not self._valid_prim:
                self._valid_prim = prim
                self._layer = type(prim)._layer
                self._dev_specific = isinstance(prim, DeviceTarget)
                if self._dev_specific:
                    self[prim._device_index] = prim
                else:
                    self[0] = prim
            elif not self._dev_specific:
                raise ValueError("Only one non device specific prim "
                                 "allowed in a Frame at once.")
            elif self._group_type == prim._group_type\
                 and self._prim_type == type(prim):
                self[prim._device_index] = prim
            else:
                raise ValueError("Incompatible primitives")
        return self

    def fill(self):
        if not self._valid_prim:
            raise ValueError("No valid primitives inserted before fill.")
        if self._dev_specific:
            for i, p in enumerate(self):
                if p is None:
                    self[i] = self._valid_prim.get_placeholder_for_dev(
                        self._chain._devices[i])
        return self

    @property
    def _group_type(self):
        return self._valid_prim._group_type

    @property
    def _prim_type(self):
        return type(self._valid_prim)

    def __len__(self):
        return len(self._prims)

    def __delitem__(self, index):
        self._prims.__delitem__(index)

    def insert(self, index, value):
        self._prims.insert(index, value)

    def __setitem__(self, index, value):
        self._prims.__setitem__(index, value)

    def __getitem__(self, index):
        return self._prims.__getitem__(index)

    def __repr__(self):
        return "<Frame%s>"%self._prims

    @classmethod
    def from_prim(cls, chain, *prim):
        return cls(chain, *prim, fill=True)

    def expand_macro(self):
        return type(self._valid_prim).expand_frame(self)
        res = []
        dat = type(self._valid_prim).expand_frame(self)
        for newfdat in dat:
            newf = Frame(self._chain, *newfdat)
            newf.fill()
            res.append(newf)
        return res

    def signature(self):
        return self._valid_prim.signature()


class FrameSequence(collections.MutableSequence):
    def __init__(self, chain, *init_prims_lists):
        self._chain = chain
        self._frames = []
        if isinstance(init_prims_lists[0], Frame):
            for frame in init_prims_lists:
                self._frames.append(frame)
        else:
            for p in init_prims_lists[0]:
                self._frames.append(Frame(self._chain, p))
            for ps in init_prims_lists[1:]:
                self.addstream(ps)

    #Needleman–Wunsch algorithm
    def _lcs(self, prims):
        #Initialize with 0
        lengths = [[0 for j in range(len(prims)+1)]
                   for i in range(len(self)+1)]
        for i, f in enumerate(self):
            for j, p in enumerate(prims):
                if f.signature() == p.signature():
                    lengths[i+1][j+1] = lengths[i][j] + 1
                else:
                    lengths[i+1][j+1] = max(lengths[i+1][j],
                                            lengths[i][j+1])
        result = []
        x, y = len(self), len(prims)
        while x != 0 and y != 0:
            if lengths[x][y] == lengths[x-1][y]:
                x -= 1
            elif lengths[x][y] == lengths[x][y-1]:
                y -= 1
            else:
                result = [self[x-1].signature()] + result
                x -= 1
                y -= 1
        return result

    def addstream(self, prims):
        i1, i2, selfoffset = 0, 0, 0
        for c in self._lcs(prims):
            while True:
                if self[i1].signature() ==\
                   prims[i2].signature() == c:
                    self._frames[i1].add(prims[i2])
                    i1 += 1
                    i2 += 1
                    break
                elif self[i1].signature() == c: #s2 does not match.
                    self.insert(i1+selfoffset,
                                Frame.from_prim(self._chain,prims[i2]))
                    i2 += 1
                    selfoffset += 1
                elif (type(prims[i2]),prims[i2]._group_type) == c:
                    #s1 does not match.
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

    def finalize(self):
        for f in self._frames:
            f.fill()
        return self

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

    def insert(self, index, val):
        self._frames.insert(index, val)

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
