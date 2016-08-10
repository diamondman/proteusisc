#!/usr/bin/env python

import time
from bitarray import bitarray
from flask import Flask, escape, render_template

from pprint import pprint

import sys
sys.path.append("/home/diamondman/src/proteusisc")

import proteusisc
from proteusisc.controllerManager import _controllerfilter
from proteusisc.jtagScanChain import JTAGScanChain
from proteusisc.frame import FrameSequence
from proteusisc.jtagDevice import JTAGDevice
from proteusisc import errors as proteusiscerrors
from proteusisc.primitive import DeviceTarget
from proteusisc.test_utils import FakeDev

drvr = _controllerfilter[0x1443][None]
c = drvr(FakeDev())
chain = JTAGScanChain(c)

devid = bitarray('11110110110101001100000010010011')
d0 = chain.initialize_device_from_id(chain, devid)
d1 = chain.initialize_device_from_id(chain, devid)
d2 = chain.initialize_device_from_id(chain, devid)
#d3 = chain.initialize_device_from_id(chain, devid)
chain._hasinit = True
chain._devices = [d0, d1, d2]#, d3]

a = d0.run_instruction("ISC_ENABLE", read=True, data=bitarray(bin(7)[2:].zfill(8)))
b = d0.run_instruction("ISC_ENABLE", read=False, loop=8, delay=0.01)
#for r in (bitarray(bin(i)[2:].zfill(8)) for i in range(2)):
#    d0.run_instruction("ISC_PROGRAM", read=False, data=r, loop=8, delay=0.01)
#d1.run_instruction("ISC_ENABLE", read=False, delay=0.01)
#d1.run_instruction("ISC_ENABLE", read=False, execute=False, data=bitarray(), delay=0.01)
#d1.run_instruction("ISC_ENABLE", read=False, loop=8, delay=0.01)
#for r in (bitarray(bin(i)[2:].zfill(8)) for i in range(4,6)):
#    d2.run_instruction("ISC_PROGRAM", read=False, data=r, loop=8, delay=.01)
#d0.run_instruction("ISC_DISABLE", loop=8, delay=0.01)
#d0.run_instruction("ISC_PROGRAM", read=False, data=bitarray(bin(7)[2:].zfill(8)), loop=8, delay=0.01)
#chain.transition_tap("TLR")
#d0.rw_dev_dr(data=bitarray("1001"))
#d2.rw_dev_dr(data=bitarray("1001"))
chain.sleep(delay=1)
chain.sleep(delay=2)
chain.sleep(delay=1)
chain.sleep(delay=2)
chain.sleep(delay=1)

app = Flask(__name__)

@app.route('/')
def report():
    if len(chain._command_queue) == 0:
        return "No commands in Queue."
    t = time.time()
    stages = []

    ######################### STAGE 01 #########################
    ###################### INITIAL PRIMS! ######################

    stages.append([chain.snapshot_queue()])

    ######################### STAGE 02 #########################
    ############### GROUPING BY EXEC BOUNDARIES!################

    fences = []
    fence = [chain._command_queue[0]]
    for p in chain._command_queue[1:]:
        if type(fence[0])._layer == type(p)._layer and\
           isinstance(fence[0], DeviceTarget) == \
              isinstance(p, DeviceTarget):
            fence.append(p)
        else:
            fences.append(fence)
            fence = [p]
    fences.append(fence)

    formatted_fences = []
    for fence in fences:
        formatted_fence = [p.snapshot() for p in fence]
        formatted_fences.append(formatted_fence)
        formatted_fences.append([])
    stages.append(formatted_fences[:-1]) #Ignore trailing []

    ######################### STAGE 03 #########################
    ############## SPLIT GROUPS BY DEVICE TARGET! ##############

    split_fences = []
    for fence in fences:
        tmp_chains = {}
        for p in fence:
            k = p._device_index \
                if isinstance(p, DeviceTarget) else "chain"
            subchain = tmp_chains.setdefault(k, []).append(p)
        split_fences.append(list(tmp_chains.values()))

    formatted_split_fences = []
    for fence in split_fences:
        for group in fence:
            formatted_split_fences.append([p.snapshot() for p in group])
        formatted_split_fences.append([])
    stages.append(formatted_split_fences[:-1])

    ######################### STAGE 04 #########################
    ############## ALIGN SEQUENCES AND PAD FRAMES ##############

    grouped_fences = [
        FrameSequence(chain, *fence).finalize()
        for f_i, fence in enumerate(split_fences)
    ]

    formatted_grouped_fences = []
    for fence in grouped_fences:
        formatted_grouped_fences += fence.snapshot() + [[]]
    stages.append(formatted_grouped_fences[:-1])

    ######################### STAGE 05 #########################
    ################## RECOMBINE FRAME GROUPS ##################

    combined_fences = grouped_fences[0]
    for fence in grouped_fences[1:]:
        combined_fences += fence

    stages.append(combined_fences.snapshot())

    ######################### STAGE 06 #########################
    ################ TRANSLATION TO LOWER LAYER ################

    expanded_prims = FrameSequence(chain)
    for f in combined_fences:
        if f._layer == 3:
            expanded_prims += f.expand_macro()
        elif f._layer == 2:
            expanded_prims.append(f)
    expanded_prims.finalize()

    stages.append(expanded_prims.snapshot())

    ######################### STAGE 07 #########################
    ################# COMBINE COMPATIBLE PRIMS #################

    merged_prims = FrameSequence(chain)
    working_prim = expanded_prims[0]
    i = 1
    while i < len(expanded_prims):
        tmp = expanded_prims[i]
        res = working_prim.merge(tmp)
        if res is not None:
            working_prim = res
        else:
            merged_prims.append(working_prim)
            working_prim = tmp
        i += 1
    merged_prims.append(working_prim)

    stages.append(merged_prims.snapshot())

    ######################### STAGE 08 #########################
    ################ TRANSLATION TO LOWER LAYER ################

    expanded_prims2 = FrameSequence(chain)
    for f in merged_prims:
        if f._layer == 3:
            raise Exception("There should be no lv3 prims at this stage")
        if issubclass(f._prim_type, DeviceTarget):
            expanded_prims2 += f.expand_macro()
        else:
            expanded_prims2.append(f)
    #expanded_prims2.finalize() #Necessary?

    stages.append(expanded_prims2.snapshot())

    ######################### STAGE 09 #########################
    ################# COMBINE COMPATIBLE PRIMS #################

    merged_prims2 = FrameSequence(chain)
    working_prim = expanded_prims2[0]
    i = 1
    while i < len(expanded_prims2):
        tmp = expanded_prims2[i]
        res = working_prim.merge(tmp)
        if res is not None:
            working_prim2 = res
        else:
            merged_prims2.append(working_prim)
            working_prim = tmp
        i += 1
    merged_prims2.append(working_prim)

    stages.append(merged_prims2.snapshot())

    ######################### STAGE 10 #########################
    ################ TRANSLATION TO LOWER LAYER ################

    expanded_prims3 = FrameSequence(chain)
    for f in merged_prims2:
        if f._layer == 3 or issubclass(f._prim_type, DeviceTarget):
            raise Exception("Invalid prims at this stage.")
        tmp = f.expand_macro()
        if tmp:
            expanded_prims3 += tmp
        else:
            expanded_prims3.append(f)
    #expanded_prims3.finalize() #Necessary?

    stages.append(expanded_prims3.snapshot())

    ######################### !!END!! ##########################

    print(time.time()-t)

    return render_template("layout.html", stages=stages,
                           dev_count=len(chain._devices))

if __name__ == "__main__":
    app.run(debug=True)
