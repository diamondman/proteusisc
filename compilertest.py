#!/usr/bin/env python
import os
import sys
import types
import time
import collections
from bitarray import bitarray

import ipdb
from pprint import pprint

sys.path.append("/home/diamondman/src/proteusisc")

import proteusisc
from proteusisc.controllerManager import _controllerfilter
from proteusisc.jtagScanChain import JTAGScanChain
from proteusisc.jtagDevice import JTAGDevice
from proteusisc import errors as proteusiscerrors
from proteusisc.primative import DefaultRunInstructionPrimative

class Frame(collections.MutableSequence):
    def __init__(self, chain, *prims, autofill=False):
        self._chain = chain
        self._inner_list = [None for i in range(len(chain._devices))]
        self._valid_prim = None
        if prims:
            self.add(*prims)
        if autofill:
            self.fill()

    def add(self, *args):
        for prim in args:
            self[prim._device_index] = prim
            if not self._valid_prim:
                self._valid_prim = prim

    def fill(self):
        if not self._valid_prim:
            raise ValueError("No valid primitives inserted before fill called")
        for i, p in enumerate(self):
            if p is None:
                self[i] = self._valid_prim.get_placeholder_for_dev(
                    self._chain._devices[i])

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


class FakeDevHandle(object):
    def __init__(self):
        self.data = []
    def controlRead(self, a, b, c, d, l):
        if not self.data:
            d = b"MOCK"
        else:
            d = self.data[0]
            self.data = self.data[1:]
        return d
    def bulkWrite(self, a, b):
        if not self.data:
            d = b"MOCK"
            raise Exception()
        else:
            d = self.data[0]
            self.data = self.data[1:]
        return d
    def bulkRead(self, infnum, l):
        if not self.data:
            d = b"MOCK"
            raise Exception()
        else:
            d = self.data[0]
            self.data = self.data[1:]
        return d

    def close(self):
        pass
    def addData(self, *datas):
        self.data += datas


class FakeDev(object):
    def open(self):
        return FakeDevHandle()

drvr = _controllerfilter[0x1443][None]
c = drvr(FakeDev())
chain = JTAGScanChain(c)

d0 = chain.initialize_device_from_id(chain,
            bitarray('11110110110101001100000010010011'))
d1 = chain.initialize_device_from_id(chain,
            bitarray('11110110110101001100000010010011'))
d2 = chain.initialize_device_from_id(chain,
            bitarray('11110110110101001100000010010011'))
#d3 = chain.initialize_device_from_id(chain,
#            bitarray('11110110110101001100000010010011'))
chain._hasinit = True
chain._devices = [d0, d1, d2]#, d3]

d0.run_tap_instruction("ISC_ENABLE", read=False, delay=0.01)
d0.run_tap_instruction("ISC_ENABLE", read=False, loop=8, delay=0.01, execute=False)
for r in (bitarray(bin(i)[2:].zfill(8)) for i in range(2)):
    d0.run_tap_instruction("ISC_PROGRAM", read=False, arg=r, loop=8, delay=0.01)


d1.run_tap_instruction("ISC_ENABLE", read=False, delay=0.01)
d1.run_tap_instruction("ISC_ENABLE", read=False, delay=0.01)

#chain.transition_tap("TLR")
##chain.transition_tap("TLR")
#d2.run_tap_instruction("ISC_ENABLE", read=False, delay=0.01)

d1.run_tap_instruction("ISC_ENABLE", read=False, loop=8, delay=0.01)
#for r in (bitarray(bin(i)[2:].zfill(8)) for i in range(4,6)):
#    d2.run_tap_instruction("ISC_PROGRAM", read=False, arg=r, loop=8, delay=.01)

#d0.run_tap_instruction("ISC_INIT", loop=8, delay=0.01) #DISCHARGE

d0.run_tap_instruction("ISC_INIT", loop=8, arg=bitarray(), delay=0.01)

d0.run_tap_instruction("ISC_DISABLE", loop=8, delay=0.01)#, expret=bitarray('00010101'))

#d0.run_tap_instruction("BYPASS")#, expret=bitarray('00100101'))

#d0._chain.transition_tap("TLR")


class Plural(object):
    def __init__(self, *prims):
        pass


def snap_queue_item(p):
    return {'dev':p.target_device.chain_index if hasattr(p, 'target_device') else "CHAIN",
             'name':getattr(p, '_function_name', None) or \
             getattr(type(p), 'name', None) or \
             type(p).__name__,
            'synthetic': p._synthetic if hasattr(p, '_synthetic') else False,
            'layer': type(p)._layer,
            'grouping': p._group_type,
            'data':{
                attr.replace("insname","INS"):
                getattr(p, attr)
                for attr in vars(p)
                if attr[0] != '_' and
                attr not in ["name", "target_device", "required_effect"] and
                getattr(p, attr) is not None and
                not isinstance(getattr(p, attr), types.FunctionType)
            },
    }

def snap_queue_state(queue):
    return [snap_queue_item(p) for p in queue]

#Needleman–Wunsch algorithm
def lcs(a, b):
    lengths = [[0 for j in range(len(b)+1)] for i in range(len(a)+1)]
    # row 0 and column 0 are initialized to 0 already
    for i, x in enumerate(a):
        for j, y in enumerate(b):
            if x == y:
                lengths[i+1][j+1] = lengths[i][j] + 1
            else:
                lengths[i+1][j+1] = max(lengths[i+1][j], lengths[i][j+1])
    result = []
    x, y = len(a), len(b)
    while x != 0 and y != 0:
        if lengths[x][y] == lengths[x-1][y]:
            x -= 1
        elif lengths[x][y] == lengths[x][y-1]:
            y -= 1
        else:
            result = [a[x-1]] + result
            x -= 1
            y -= 1
    return result


from flask import Flask, escape, render_template
app = Flask(__name__)

@app.route('/')
def report():
    t = time.time()
    stages = []

    ####################### STAGE 1 ############################

    stages.append([snap_queue_state(chain._command_queue.queue)])

    ####################### STAGE 2 ############################

    fences = []
    fence = [chain._command_queue.queue[0]]
    for p in chain._command_queue.queue[1:]:
        if type(fence[0])._layer == type(p)._layer:
            fence.append(p)
        else:
            fences.append(fence)
            fence = [p]
    fences.append(fence)

    formatted_fences = []
    for fence in fences:
        formatted_fence = [snap_queue_item(p) for p in fence]
        formatted_fences.append(formatted_fence)
        formatted_fences.append([])
    stages.append(formatted_fences[:-1]) #Ignore trailing []

    ####################### STAGE 3 ############################

    split_fences = []
    for fence in fences:
        tmp_chains = {}
        for p in fence:
            k = p.target_device.chain_index \
                if hasattr(p, 'target_device') else "chain"
            subchain = tmp_chains.setdefault(k, []).append(p)
        split_fences.append(list(tmp_chains.values()))

    formatted_split_fences = []
    for fence in split_fences:
        for group in fence:
            formatted_fence = [snap_queue_item(p) for p in group]
            formatted_split_fences.append(formatted_fence)
        formatted_split_fences.append([])
    stages.append(formatted_split_fences[:-1])

    ####################### STAGE 4 ############################

    #TODO HANDLE OTHER CASES (lower level prims, lanes>3)
    grouped_fences = []
    for f_i, fence in enumerate(split_fences):
        if len(fence) == 1:
            grouped_fences.append(
                [Frame.from_prim(chain, p) for p in fence[0]])
        else: # 2 or more
            s1, s2 = fence
            seq = lcs([x._group_type for x in s1],
                      [x._group_type for x in s2])
            out = []
            i1, i2 = 0, 0
            for c in seq:
                while True:
                    elem1, elem2 = s1[i1], s2[i2]
                    if elem1._group_type == elem2._group_type == c:
                        out.append(Frame.from_prim(chain, elem1, elem2))
                        i1 += 1
                        i2 += 1
                        break
                    elif elem1._group_type == c: #s2 does not match.
                        out.append(Frame.from_prim(chain, elem2))
                        i2 += 1
                    elif elem2._group_type == c: #s1 does not match.
                        out.append(Frame.from_prim(chain, elem1))
                        i1 += 1
                    else: #NEITHER IN SEQUENCE Not tested.
                        out.append(Frame.from_prim(chain,elem1))
                        out.append(Frame.from_prim(chain,elem2))
                        i1 += 1
                        i2 += 1

            for p in s1[i1:] + s2[i2:]:
                out.append(Frame.from_prim(chain, p))

            print(out)
            grouped_fences.append(out)

    formatted_grouped_fences = []
    for fence in grouped_fences:
        print("FENCE",fence)
        tracks = [[] for i in range(len(chain._devices))]
        for combined_prim in fence:
            print("    GROUP",combined_prim)
            for p in combined_prim:
                tracks[p._device_index or 0]\
                    .append(snap_queue_item(p))
        print("    APPENDING", tracks)
        print()
        formatted_grouped_fences += tracks
        formatted_grouped_fences.append([])

    stages.append(formatted_grouped_fences[:-1])
    #pprint(stages)

    pprint(stages[-1])
    print(time.time()-t)

    return render_template("layout.html",
                            stages=stages)

if __name__ == "__main__":
    app.run(debug=True)
