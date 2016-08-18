#!/usr/bin/env python
#Must be run from the project directory.

import time
from bitarray import bitarray
from flask import Flask, escape, render_template

from pprint import pprint

import proteusisc
from proteusisc.controllerManager import _controllerfilter
from proteusisc.jtagScanChain import JTAGScanChain
from proteusisc.jtagStateMachine import JTAGStateMachine
from proteusisc.frame import FrameSequence
from proteusisc.jtagDevice import JTAGDevice
from proteusisc import errors as proteusiscerrors
from proteusisc.primitive import DeviceTarget, Level3Primitive,\
    Level2Primitive, ExpandRequiresTAP, Executable
from proteusisc.test_utils import FakeDev

#drvr = _controllerfilter[0x03FD][0x0008]
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
b = d0.run_instruction("ISC_ENABLE", read=False, execute=False, data=bitarray(bin(7)[2:].zfill(14)))#loop=8, delay=0.01)
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
#chain.rw_reg(data=bitarray('11001010'))
chain.sleep(delay=1)
chain.sleep(delay=2)
chain.sleep(delay=1)
chain.sleep(delay=2)
chain.sleep(delay=1)

def mergePrims(inchain):
    if isinstance(inchain, FrameSequence):
        merged_prims = FrameSequence(chain)
    else:
        merged_prims = []
    working_prim = inchain[0]
    i = 1
    while i < len(inchain):
        tmp = inchain[i]
        res = working_prim.merge(tmp)
        if res is not None:
            working_prim = res
        else:
            merged_prims.append(working_prim)
            working_prim = tmp
        i += 1
    merged_prims.append(working_prim)
    return merged_prims


app = Flask(__name__)

@app.route('/')
def report():
    if len(chain._command_queue) == 0:
        return "No commands in Queue."
    t = time.time()
    stages = []
    stagenames = []

    ######################### STAGE 01 #########################
    ###################### INITIAL PRIMS! ######################

    stages.append([chain.snapshot_queue()])
    stagenames.append("Input Stream")

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
    stagenames.append("Fencing off execution boundaries")

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
    stagenames.append("Grouping prims of each boundary by target device")

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
    stagenames.append("Aligning and combining each group dev prim stream")

    ######################### STAGE 05 #########################
    ################## RECOMBINE FRAME GROUPS ##################

    ingested_chain = grouped_fences[0]
    for fence in grouped_fences[1:]:
        ingested_chain += fence

    stages.append(ingested_chain.snapshot())
    stagenames.append("Recombining sanitized execution boundaries")

    ###################### POST INGESTION ######################
    ######################### STAGE 6+ #########################
    ################ Flatten out LV3 Primitives ################
    while(any((f._layer == 3 for f in ingested_chain))):
        ################# COMBINE COMPATIBLE PRIMS #################
        ingested_chain = mergePrims(ingested_chain)

        stages.append(ingested_chain.snapshot())
        stagenames.append("Combining compatible lv3 prims.")

        ################ TRANSLATION TO LOWER LAYER ################
        sm = JTAGStateMachine(chain._sm.state)
        expanded_prims = FrameSequence(chain)
        for f in ingested_chain:
            if f._layer == 3:
                expanded_prims += f.expand_macro(sm)
            else:
                expanded_prims.append(f)
        expanded_prims.finalize()
        ingested_chain = expanded_prims

        stages.append(ingested_chain.snapshot())
        stagenames.append("Expanding lv3 prims")


    ######################### STAGE 8+ #########################
    ############## Flatten out Dev LV2 Primitives ##############
    while(any((isinstance(f._valid_prim, DeviceTarget)
               for f in ingested_chain))):
        ################# COMBINE COMPATIBLE PRIMS #################

        ingested_chain = mergePrims(ingested_chain)

        stages.append(ingested_chain.snapshot())
        stagenames.append("Merging Device Specific Prims")

        ################ TRANSLATION TO LOWER LAYER ################

        sm = JTAGStateMachine(chain._sm.state)
        expanded_prims = FrameSequence(chain)
        for f in ingested_chain:
            if issubclass(f._prim_type, DeviceTarget):
                expanded_prims += f.expand_macro(sm)
            else:
                expanded_prims.append(f)
        expanded_prims.finalize()
        ingested_chain = expanded_prims

        stages.append(ingested_chain.snapshot())
        stagenames.append("Expanding Device Specific Prims")

    ############ Convert FrameSequence to flat array ###########
    flattened_prims = [f._valid_prim for f in ingested_chain]
    stages.append([[p.snapshot() for p in flattened_prims]])
    stagenames.append("Converting format to single stream.")

    del ingested_chain

    ####################### STAGE 10+ #########################
    ######### Flatten out remaining macros Primitives #########
    while (not all((isinstance(p, (ExpandRequiresTAP,Executable))
                    for p in flattened_prims))):
        ################# COMBINE COMPATIBLE PRIMS #################
        flattened_prims = mergePrims(flattened_prims)

        stages.append([[p.snapshot() for p in flattened_prims]])
        stagenames.append("Merging Device Agnostic LV2 Prims")

        ################ TRANSLATION TO LOWER LAYER ################
        sm = JTAGStateMachine(chain._sm.state)
        expanded_prims = []
        for p in flattened_prims:
            tmp = p.expand(chain, sm) if not \
                  isinstance(p, ExpandRequiresTAP) else None
            if tmp:
                expanded_prims += tmp
            else:
                expanded_prims.append(p)
        flattened_prims = expanded_prims

        stages.append([[p.snapshot() for p in flattened_prims]])
        stagenames.append("Expanding Device Agnostic LV2 Prims")


    ################# COMBINE COMPATIBLE PRIMS #################
    flattened_prims = mergePrims(flattened_prims)

    stages.append([[p.snapshot() for p in flattened_prims]])
    stagenames.append("Final LV2 merge")

    ################### EXPAND TO LV1 PRIMS ####################
    sm = JTAGStateMachine(chain._sm.state)
    expanded_prims = []
    for p in flattened_prims:
        tmp = p.expand(chain, sm)
        if tmp:
            expanded_prims += tmp
        else:
            expanded_prims.append(p)
    flattened_prims = expanded_prims

    stages.append([[p.snapshot() for p in flattened_prims]])
    stagenames.append("Expand to LV1 Primitives")


    if not all((isinstance(p, Executable) for p in flattened_prims)):
        raise proteusiscerrors.ProteusISCException(
            "Reduction did not produce executable instruction sequence.")


    #################### COMBINE LV1 PRIMS #####################

    flattened_prims = mergePrims(flattened_prims)

    stages.append([[p.snapshot() for p in flattened_prims]])
    stagenames.append("Final LV2 merge")

    ############################################################

    print(time.time()-t)

    return render_template("layout.html", stages=stages,
                           stagenames=stagenames,
                           dev_count=len(chain._devices))

if __name__ == "__main__":
    app.run(debug=True)
