#!/usr/bin/env python
import os
import sys
import types
from bitarray import bitarray
import ipdb

sys.path.append("/home/diamondman/src/proteusisc")

import proteusisc
from proteusisc.controllerManager import _controllerfilter
from proteusisc.jtagScanChain import JTAGScanChain
from proteusisc.jtagDevice import JTAGDevice
from proteusisc import errors as proteusiscerrors

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


#c._handle.addData(None, [1,0], #JTAG ON
#                  None, [1,0], None, None, None, #STATE SHIFTDR
#                  None, [1,0], bitarray(bitarray('11110110110101001100000010010011')).tobytes()[::-1], None, None, #DEV 1
#                  None, [1,0], bitarray(bitarray('11110110110101001100000010010011')).tobytes()[::-1], None, None, #DEV 2
#                  None, [1,0], bitarray(bitarray('0'*32)).tobytes()[::-1], None, None, #EOF
#                  None, [1,0], #JTAG OFF
#                  None, [1,0], #JTAG ON
#)


c = drvr(FakeDev())
chain = JTAGScanChain(c)

d0 = chain.initialize_device_from_id(chain,
            bitarray('11110110110101001100000010010011'))
d1 = chain.initialize_device_from_id(chain,
            bitarray('11110110110101001100000010010011'))
chain._hasinit = True
chain._devices = [d0, d1]

d0.run_tap_instruction("BYPASS", read=False, delay=0.01)
d0.run_tap_instruction("ISC_ENABLE", read=False, loop=8, delay=0.01, execute=False)
for r in (bitarray(bin(i)[2:].zfill(8)) for i in range(2)):
    d0.run_tap_instruction("ISC_PROGRAM", read=False, arg=r, loop=8, delay=0.01)


d1.run_tap_instruction("BYPASS", read=False, delay=0.01)
d1.run_tap_instruction("BYPASS", read=False, delay=0.01)

#chain.transition_tap("TLR")
#chain.transition_tap("TLR")
d0.run_tap_instruction("BYPASS", read=False, delay=0.01)

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


from flask import Flask, escape, render_template
app = Flask(__name__)

@app.route('/')
def report():
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
        print("FENCE",fence)
        print()
        for group in fence:
            #print("GROUP",group)
            #print()
            formatted_fence = [snap_queue_item(p) for p in group]
            formatted_split_fences.append(formatted_fence)
        formatted_split_fences.append([])

    stages.append(formatted_split_fences[:-1])

    #################################################

    for f_i, fence in enumerate(split_fences):
        if len(fence) == 2:
            print("RUNNING")
            print(fence[0])
            print(fence[1])
            s1 = [x.execute for x in fence[0]]
            s2 = [x.execute for x in fence[1]]
            seq = lcs(s1, s2)
            o1 = []
            o2 = []
            i1,i2 = 0,0
            seq_i = 0
            iterc = 0
            for c in seq:
                #print(s1[i1],s2[i2], c)
                loop = True
                while loop:
                    iterc += 1

                    if s1[i1] == s2[i2]:
                        o1.append(s1[i1])
                        o2.append(s2[i2])
                        i1 += 1
                        i2 += 1
                        loop=False
                    elif s1[i1] == c: #s2 does not match
                        o1.append(None)
                        o2.append(s2[i2])
                        i2 += 1
                    elif s2[i2] == c: #s1 does not match
                        o1.append(s1[i1])
                        o2.append(None)
                        i1 += 1
                    else:
                        o1.append(s1[i1])
                        o2.append(s2[i2])
                        i1 += 1
                        i2 += 1
            o1 += s1[i1:]
            o2 += s2[i2:]

            print(o1)
            print(o2)




    #merged_fences = []
    #for f_i, fence in enumerate(split_fences):
    #    g_indexes = [0 for i in range(len(fence))]
    #    loop=True
    #    while loop:
    #        current_comb = []
    #        for g_i, group in enumerate(fence):
    #            #Do not do multiple iters. Just check next one.
    #            for other_g_i, other_group in enumerate(fence):
    #                if other_g_i==g_i: continue
    #                if group[g_indexes[g_i]]\
    #                         .mergable(other_group[g_indexes[other_g_i]]):
    #                    print(f_i, g_i, g_indexes[g_i],"AND",
    #                          f_i, other_g_i, g_indexes[other_g_i])
    #
    #
    #        loop = False

    #    tmp_chains = {}
    #    for p in fence:
    #        k = p.target_device.chain_index \
    #            if hasattr(p, 'target_device') else "chain"
    #        subchain = tmp_chains.setdefault(k, [])
    #        subchain.append(snap_queue_item(p))
    #
    #    formatted_split_fences+=list(tmp_chains.values())+[[]]#'layer':-1}]
    #formatted_split_fences = formatted_split_fences[:-1] #Remove end split
    #
    stages.append([[snap_queue_item(split_fences[0][0][0])]])


    #import ipdb
    #ipdb.set_trace()

    return render_template("layout.html",
                            stages=stages)




if __name__ == "__main__":
    app.run(debug=True)
