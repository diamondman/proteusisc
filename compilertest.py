#!/usr/bin/env python
import os
import sys
import types
from bitarray import bitarray
import ipdb
import time

sys.path.append("/home/diamondman/src/proteusisc")

import proteusisc
from proteusisc.controllerManager import _controllerfilter
from proteusisc.jtagScanChain import JTAGScanChain
from proteusisc.jtagDevice import JTAGDevice
from proteusisc import errors as proteusiscerrors
from proteusisc.primative import DefaultRunInstructionPrimative

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
chain.transition_tap("TLR")
d0.run_tap_instruction("ISC_ENABLE", read=False, delay=0.01)

d1.run_tap_instruction("ISC_ENABLE", read=False, loop=8, delay=0.01)
for r in (bitarray(bin(i)[2:].zfill(8)) for i in range(4,6)):
    d1.run_tap_instruction("ISC_PROGRAM", read=False, arg=r, loop=8, delay=0.01)

#d0.run_tap_instruction("ISC_INIT", loop=8, delay=0.01) #DISCHARGE

#d0.run_tap_instruction("ISC_INIT", loop=8, arg=bitarray(), delay=0.01)

#d0.run_tap_instruction("ISC_DISABLE", loop=8, delay=0.01)#, expret=bitarray('00010101'))

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
            'layer': type(p)._layer,
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
    #from pprint import pprint
    #pprint(lengths)
    # read the substring out from the matrix
    result = []
    x, y = len(a), len(b)
    while x != 0 and y != 0:
        if lengths[x][y] == lengths[x-1][y]:
            x -= 1
        elif lengths[x][y] == lengths[x][y-1]:
            y -= 1
        else:
            #assert a[x-1] == b[y-1]
            result = [a[x-1]] + result
            x -= 1
            y -= 1
    return result

def make_single_prim_frame(p):
    p_index = p._device_index
    return\
        [DefaultRunInstructionPrimative(
            chain._devices[i], read=False,
            insname="BYPASS", execute=p.execute)
         if p_index != i else p
         for i in range(len(chain._devices))]


from flask import Flask, escape, render_template
app = Flask(__name__)

@app.route('/')
def report():
    t = time.time()
    stages = []
    stages.append([snap_queue_state(chain._command_queue.queue)])

    #########################################

    fences = []
    fence = []
    for p in chain._command_queue.queue:
        if len(fence) == 0:
            fence.append(p)
            continue
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

    ###############################################

    split_fences = []
    #Fences is a list of prims split by immobile boundaries
    #Fence is a single one of these regions
    #Split fences is a list of all the fence values, each split into a
    #list of groups. Each group is a list of prims. Three arrays deep.

    #fences[0] = [<prim>, <prim>, <prim>]
    #split_fences = [[[<prim D1>, <prim D1>], [<prim D2>, <prim D2>]],
    #                Another Fence]
    for fence in fences:
        #tmp_chain = {<D1>: [<prim>, <prim>, <prim>], <D2>: [...]}
        #list(_) = [[<prim D1>, <prim D1>], [<prim D2>, <prim D2>]]
        #print()
        #print("FENCE", fence)

        tmp_chains = {}
        for p in fence:
            k = p.target_device.chain_index \
                if hasattr(p, 'target_device') else "chain"
            subchain = tmp_chains.setdefault(k, []).append(p)

        #print("  =>",list(tmp_chains.values()))
        split_fences.append(list(tmp_chains.values()))#+[[]]#'layer':-1}]

    #print("\nRESULT")
    #print(split_fences)

    formatted_split_fences = []
    for fence in split_fences:
        #print("FENCE",fence)
        #print()
        for group in fence:
            #print("GROUP",group)
            #print()
            formatted_fence = [snap_queue_item(p) for p in group]
            formatted_split_fences.append(formatted_fence)
        formatted_split_fences.append([])

    stages.append(formatted_split_fences[:-1])

    ####################### STAGE 4 ############################

    grouped_fences = []
    for f_i, fence in enumerate(split_fences):
        if len(fence) == 1:
            grouped_fences.append([fence[0]])
        elif len(fence) == 2:
            s1, s2 = fence
            seq = lcs([x.execute for x in s1], [x.execute for x in s2])
            out = []
            i1, i2 = 0, 0
            for c in seq:
                loop = True
                while loop:
                    frame = [None for i in range(len(chain._devices))]
                    elem1, elem2 = s1[i1], s2[i2]
                    valid_prim = elem1
                    if s1[i1].execute == s2[i2].execute:
                        frame[elem1._device_index] = elem1
                        frame[elem2._device_index] = elem2
                        i1 += 1
                        i2 += 1
                        loop=False
                    elif elem1.execute == c and elem2.execute != c:
                        #s2 does not match. Can be combined with next one
                        frame[elem2._device_index] = elem2
                        i2 += 1
                    elif elem2.execute == c and elem1.execute != c:
                        #s1 does not match. Can be combined with prev one
                        frame[elem1._device_index] = elem1
                        i1 += 1
                    else: #NEITHER IN SEQUENCE
                        #Not tested. Infrequently used
                        valid_prim = elem1
                        out.append(make_single_prim_frame(elem1))
                        out.append(make_single_prim_frame(elem2))
                        i1 += 1
                        i2 += 1
                        continue

                    for i, p in enumerate(frame):
                        if p is None:
                            frame[i] = DefaultRunInstructionPrimative(
                                chain._devices[i], read=False,
                                insname="BYPASS",
                                execute=valid_prim.execute)
                    out.append(frame)

            for p in s1[i1:] + s2[i2:]:
                out.append(make_single_prim_frame(p))

            print(out)

            #TODO HANDLE OTHER CASES (multichain, lower level prims, etc)

            grouped_fences.append(out)

    formatted_grouped_fences = []
    for fence in grouped_fences:
        print("FENCE",fence)
        tracks = [[] for i in range(len(chain._devices))]
        for combined_prim in fence:
            print("    GROUP",combined_prim)

            for p in combined_prim:
                #print(p._device_index)
                tracks[p._device_index or 0]\
                    .append(snap_queue_item(p))
            #formatted_split_fences.append(formatted_fence)
        #print(*[len(t) for t in tracks])
        print("    APPENDING", tracks)
        print()
        formatted_grouped_fences += tracks
        formatted_grouped_fences.append([])

    #ipdb.set_trace()

    stages.append(formatted_grouped_fences[:-1])
    from pprint import pprint
    #pprint(stages)

    pprint(stages[-1])
    print(time.time()-t)



    return render_template("layout.html",
                            stages=stages)




if __name__ == "__main__":
    app.run(debug=True)
