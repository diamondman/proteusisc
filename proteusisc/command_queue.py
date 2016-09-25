import collections

from .jtagStateMachine import JTAGStateMachine

from .jtagStateMachine import JTAGStateMachine
from .frame import FrameSequence
from .errors import ProteusISCError
from .primitive import DeviceTarget, ExpandRequiresTAP, Executable


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

    @property
    def debug(self):
        if self._chain:
            return self._chain._debug
        return False

    def append(self, elem):
        elem._chain = self._chain
        super(CommandQueue, self).append(elem)

    def _compile_device_specific_prims(self, debug=False,
                                       stages=None, stagenames=None):
                ############### GROUPING BY EXEC BOUNDARIES!################

        fences = []
        fence = [self[0]]
        for p in self[1:]:
            if type(fence[0])._layer == type(p)._layer and\
               isinstance(fence[0], DeviceTarget) == \
                  isinstance(p, DeviceTarget):
                fence.append(p)
            else:
                fences.append(fence)
                fence = [p]
        fences.append(fence)

        if debug:
            formatted_fences = []
            for fence in fences:
                formatted_fence = [p.snapshot() for p in fence]
                formatted_fences.append(formatted_fence)
                formatted_fences.append([])
            stages.append(formatted_fences[:-1]) #Ignore trailing []
            stagenames.append("Fencing off execution boundaries")

        ############## SPLIT GROUPS BY DEVICE TARGET! ##############

        split_fences = []
        for fence in fences:
            tmp_chains = {}
            for p in fence:
                k = p._device_index \
                    if isinstance(p, DeviceTarget) else "chain"
                subchain = tmp_chains.setdefault(k, []).append(p)
            split_fences.append(list(tmp_chains.values()))

        if debug:
            formatted_split_fences = []
            for fence in split_fences:
                for group in fence:
                    formatted_split_fences.append([p.snapshot()
                                                   for p in group])
                formatted_split_fences.append([])
            stages.append(formatted_split_fences[:-1])
            stagenames.append("Grouping prims of each boundary by "
                              "target device")

        ############## ALIGN SEQUENCES AND PAD FRAMES ##############
        #FIRST DEV REQUIRED LINE
        grouped_fences = [
            FrameSequence(self._chain, *fence).finalize()
            for f_i, fence in enumerate(split_fences)
        ]

        if debug:
            formatted_grouped_fences = []
            for fence in grouped_fences:
                formatted_grouped_fences += fence.snapshot() + [[]]
            stages.append(formatted_grouped_fences[:-1])
            stagenames.append("Aligning and combining each group dev "
                              "prim stream")

        ################## RECOMBINE FRAME GROUPS ##################

        ingested_chain = grouped_fences[0]
        for fence in grouped_fences[1:]:
            ingested_chain += fence

        if debug:
            stages.append(ingested_chain.snapshot())
            stagenames.append("Recombining sanitized exec boundaries")

        ###################### POST INGESTION ######################
        ################ Flatten out LV3 Primitives ################
        while(any((f._layer == 3 for f in ingested_chain))):
            ################# COMBINE COMPATIBLE PRIMS #################
            ingested_chain = mergePrims(self._chain, ingested_chain)

            if debug:
                stages.append(ingested_chain.snapshot())
                stagenames.append("Combining compatible lv3 prims.")

            ################ TRANSLATION TO LOWER LAYER ################
            sm = JTAGStateMachine(self._chain._sm.state)
            expanded_prims = FrameSequence(self._chain)
            for f in ingested_chain:
                if f._layer == 3:
                    expanded_prims += f.expand_macro(sm)
                else:
                    expanded_prims.append(f)
            expanded_prims.finalize()
            ingested_chain = expanded_prims

            if debug:
                stages.append(ingested_chain.snapshot())
                stagenames.append("Expanding lv3 prims")


        ############## Flatten out Dev LV2 Primitives ##############
        while(any((isinstance(f._valid_prim, DeviceTarget)
                   for f in ingested_chain))):
            ################# COMBINE COMPATIBLE PRIMS #################
            ingested_chain = mergePrims(self._chain, ingested_chain)

            if debug:
                stages.append(ingested_chain.snapshot())
                stagenames.append("Merging Device Specific Prims")

            ################ TRANSLATION TO LOWER LAYER ################

            sm = JTAGStateMachine(self._chain._sm.state)
            expanded_prims = FrameSequence(self._chain)
            for f in ingested_chain:
                if issubclass(f._prim_type, DeviceTarget):
                    expanded_prims += f.expand_macro(sm)
                else:
                    expanded_prims.append(f)
            expanded_prims.finalize()
            ingested_chain = expanded_prims

            if debug:
                stages.append(ingested_chain.snapshot())
                stagenames.append("Expanding Device Specific Prims")

        ############ Convert FrameSequence to flat array ###########
        flattened_prims = [f._valid_prim for f in ingested_chain]
        if debug:
            stages.append([[p.snapshot() for p in flattened_prims]])
            stagenames.append("Converting format to single stream.")

        #del ingested_chain
        return flattened_prims


    def _compile(self, debug=False, stages=None, stagenames=None,
                 dryrun=False):
        if len(self) == 0:
            return "No commands in Queue."

        ###################### INITIAL PRIMS! ######################

        if debug:
            stages.append([self._chain.snapshot_queue()])
            stagenames.append("Input Stream")

        #Sanitize input stream and render down to lv2 dev agnostic prims
        any_dev_prims = False
        for prim in self:
            if isinstance(prim, DeviceTarget):
                any_dev_prims = True
                break
        if any_dev_prims:
            flattened_prims = self._compile_device_specific_prims(
                debug=debug, stages=stages, stagenames=stagenames
            )
        else:
            flattened_prims = self

        ######### Flatten out remaining macros Primitives #########
        while (not all((isinstance(p, (ExpandRequiresTAP,Executable))
                        for p in flattened_prims))):
            ################# COMBINE COMPATIBLE PRIMS #################
            flattened_prims = mergePrims(self._chain, flattened_prims)

            if debug:
                stages.append([[p.snapshot() for p in flattened_prims]])
                stagenames.append("Merging Device Agnostic LV2 Prims")

            ################ TRANSLATION TO LOWER LAYER ################
            sm = JTAGStateMachine(self._chain._sm.state)
            expanded_prims = []
            for p in flattened_prims:
                oldstate = sm.state
                tmp = p.expand(self._chain, sm) if not \
                      isinstance(p, ExpandRequiresTAP) else \
                      p.apply_tap_effect(sm)
                if tmp:
                    tmp[0].oldstate = oldstate
                    expanded_prims += tmp
                else:
                    p.oldstate = oldstate
                    expanded_prims.append(p)
            flattened_prims = expanded_prims

            if debug:
                stages.append([[p.snapshot() for p in flattened_prims]])
                stagenames.append("Expanding Device Agnostic LV2 Prims")


        ################# COMBINE COMPATIBLE PRIMS #################
        flattened_prims = mergePrims(self._chain, flattened_prims)

        if debug:
            stages.append([[p.snapshot() for p in flattened_prims]])
            stagenames.append("Final LV2 merge")

        ################### EXPAND TO LV1 PRIMS ####################
        sm = JTAGStateMachine(self._chain._sm.state)
        expanded_prims = []
        for p in flattened_prims:
            tmp = p.expand(self._chain, sm)
            if tmp:
                expanded_prims += tmp
            else:
                expanded_prims.append(p)
        flattened_prims = expanded_prims

        if debug:
            stages.append([[p.snapshot() for p in flattened_prims]])
            stagenames.append("Expand to LV1 Primitives")


        if not all((isinstance(p, Executable) for p in flattened_prims)):
            raise ProteusISCError(
                "Reduction did not produce executable instruction sequence.")


        #################### COMBINE LV1 PRIMS #####################

        flattened_prims = mergePrims(self._chain, flattened_prims)

        if debug:
            stages.append([[p.snapshot() for p in flattened_prims]])
            stagenames.append("Final LV2 merge")

        ############################################################

        if not dryrun:
            self.queue = flattened_prims


    def flush(self):
        self.stages = []
        self.stagenames = []
        self._compile(debug=True, stages=self.stages, stagenames=self.stagenames)
        if self.debug:
            print("ABOUT TO EXEC", self.queue)
        self._chain._controller.execute(self.queue)
        self.queue = []

def mergePrims(chain, inseq):
    if isinstance(inseq, FrameSequence):
        merged_prims = FrameSequence(chain)
    else:
        merged_prims = []
    working_prim = inseq[0]
    i = 1
    while i < len(inseq):
        tmp = inseq[i]
        res = working_prim.merge(tmp)
        if res is not None:
            working_prim = res
        else:
            merged_prims.append(working_prim)
            working_prim = tmp
        i += 1
    merged_prims.append(working_prim)
    return merged_prims
