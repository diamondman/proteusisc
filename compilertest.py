#!/usr/bin/env python
import os
import sys
import types
from bitarray import bitarray

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
d0.run_tap_instruction("ISC_ENABLE", read=False, loop=8, delay=0.01)
for r in (bitarray(bin(i)[2:].zfill(8)) for i in range(2)):
    d0.run_tap_instruction("ISC_PROGRAM", read=False, arg=r, loop=8, delay=0.01)


d1.run_tap_instruction("BYPASS", read=False, delay=0.01)
d1.run_tap_instruction("BYPASS", read=False, delay=0.01)

chain.transition_tap("TLR")
chain.transition_tap("TLR")
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
        print()
        print("FENCE", fence)

        tmp_chains = {}
        for p in fence:
            k = p.target_device.chain_index \
                if hasattr(p, 'target_device') else "chain"
            subchain = tmp_chains.setdefault(k, []).append(p)

        print("  =>",list(tmp_chains.values()))
        split_fences.append(list(tmp_chains.values()))#+[[]]#'layer':-1}]

    print("\nRESULT")
    print(split_fences)

    import ipdb
    #from pprint import pprint
    #ipdb.set_trace()


    formatted_split_fences = []
    for fence in split_fences:
        print("FENCE",fence)
        print()
        for group in fence:
            print("GROUP",group)
            print()
            formatted_fence = [snap_queue_item(p) for p in group]
            formatted_split_fences.append(formatted_fence)
        formatted_split_fences.append([])
    
    stages.append(formatted_split_fences[:-1])

    #stages.append(formatted_split_fences)
    
    #from pprint import pprint
    #pprint(stages)

    #merged_fences = []
    #for fence in fences:
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
    #stages.append(formatted_split_fences)
    
    
    #import ipdb
    #ipdb.set_trace()
        
    return render_template("layout.html",
                            stages=stages)



            
if __name__ == "__main__":
    app.run(debug=True)
