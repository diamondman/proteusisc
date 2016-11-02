import collections
from time import time

from .jtagStateMachine import JTAGStateMachine
from .frame import FrameSequence
from .errors import ProteusISCError
from .primitive import DeviceTarget, ExpandRequiresTAP, Executable


class CommandQueue(collections.MutableSequence):
    """A container to stage Primitives that knows how to compile and optimize those Primitives.

    Most primitives are not directly executable by an ISC Controller,
    and must be expanded into lower level primitives until a fully
    executable list of primitives is created.

    Primitives can sometimes execute faster if combined or
    reordered. Saving up as many Primitives as possible before
    execution increases the opportunity for optimization.

    The CommandQueue is responsible for:
        - Storing primitives until they need to execute.
        - Compiling/Expanding primitives into executable primitives.
        - Optimizing the expanded primitive stream to speed up execution.

    """
    def __init__(self, chain):
        """Create a new CommandQueue to manage, compile, and run Primitives.

        Args:
            chain: A JTAGScanChain instance that this queue will be associated with.
        """
        self.queue = []
        self._fsm = JTAGStateMachine()
        self._chain = chain

    def reset(self):
        #TODO Double check if this is best way
        if self._fsm:
            self._fsm.reset()
        self.queue = []

    def snapshot(self):
        return [p.snapshot() for p in self.queue]#pragma: no cover

    def __len__(self):
        return len(self.queue)

    def __delitem__(self, index):
        self.queue.__delitem__(index)#pragma: no cover

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

    @property
    def print_statistics(self):
        if self._chain:
            return self._chain._print_statistics
        return False

    def append(self, elem):
        elem._chain = self._chain
        super(CommandQueue, self).append(elem)

    def _compile_device_specific_prims(self, debug=False,
                                       stages=None, stagenames=None):
        """Using the data stored in the CommandQueue, Extract and align compatible sequences of Primitives and compile/optimize the Primitives down into a stream of Level 2 device agnostic primitives.

        BACKGROUND:
        Device Specific primitives present a special opportunity for
        optimization. Many JTAG systems program one device on the
        chain at a time. But because all devices on a JTAG chain are
        sent information at once, NO-OP instructions are sent to these
        other devices.

        When programming multiple devices, Sending these NO-OPS is a
        missed opportunity for optimization. Instead of configuring
        one device at a time, it is more efficient to collect
        instructions for all deices, and align them so multiple
        devices can be configured at the same time.

        WAT THIS METHOD DOES:
        This method takes in a list of Primitives, groups the device
        specific primitives by target device, aligns the sequences of
        device instructions, and expands the aligned sequences into a
        flat list of device agnostic primitives.

        Args:
            debug: A boolean for if debug information should be generated.
            stages: A list to be edited by this method to store snapshots of the compilation state. Used if debug is True.
            stagenames: A list of strings describing each debug snapshot of the compiilation process. Used if debug is True.

        """
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

        if debug: #pragma: no cover
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

        if debug:#pragma: no cover
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

        if debug:#pragma: no cover
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

        if debug:#pragma: no cover
            stages.append(ingested_chain.snapshot())
            stagenames.append("Recombining sanitized exec boundaries")

        ###################### POST INGESTION ######################
        ################ Flatten out LV3 Primitives ################
        while(any((f._layer == 3 for f in ingested_chain))):
            ################# COMBINE COMPATIBLE PRIMS #################
            ingested_chain = _merge_prims(ingested_chain)

            if debug:#pragma: no cover
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

            if self._fsm is None:
                self._fsm = sm
            assert self._fsm == sm, "Target %s != Actual %s"%\
                (self._fsm.state, sm.state)

            if debug:#pragma: no cover
                stages.append(ingested_chain.snapshot())
                stagenames.append("Expanding lv3 prims")


        ############## Flatten out Dev LV2 Primitives ##############
        while(any((isinstance(f._valid_prim, DeviceTarget)
                   for f in ingested_chain))):
            ################# COMBINE COMPATIBLE PRIMS #################
            ingested_chain = _merge_prims(ingested_chain)

            if debug:#pragma: no cover
                stages.append(ingested_chain.snapshot())
                stagenames.append("Merging Device Specific Prims")

            ################ TRANSLATION TO LOWER LAYER ################

            sm = JTAGStateMachine(self._chain._sm.state)
            expanded_prims = FrameSequence(self._chain)
            for f in ingested_chain:
                if issubclass(f._prim_type, DeviceTarget):
                    expanded_prims += f.expand_macro(sm)
                else:
                    f[0].apply_tap_effect(sm)
                    expanded_prims.append(f)
            expanded_prims.finalize()
            ingested_chain = expanded_prims
            if self._fsm is None:
                self._fsm = sm
            assert self._fsm == sm, "Target %s != Actual %s"%\
                 (self._fsm.state, sm.state)

            if debug:#pragma: no cover
                stages.append(ingested_chain.snapshot())
                stagenames.append("Expanding Device Specific Prims")

        ############ Convert FrameSequence to flat array ###########
        flattened_prims = [f._valid_prim for f in ingested_chain]
        if debug:#pragma: no cover
            stages.append([[p.snapshot() for p in flattened_prims]])
            stagenames.append("Converting format to single stream.")

        return flattened_prims


    def _compile(self, debug=False, stages=None, stagenames=None,
                 dryrun=False):
        self._fsm = None
        if len(self) == 0:
            return "No commands in Queue."

        ###################### INITIAL PRIMS! ######################

        if debug:#pragma: no cover
            stages.append([self.snapshot()])
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
            flattened_prims = _merge_prims(flattened_prims)

            if debug:#pragma: no cover
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
            if self._fsm is None:
                self._fsm = sm
            assert self._fsm == sm, "Target %s != Actual %s"%\
                  (self._fsm.state, sm.state)

            if debug:#pragma: no cover
                stages.append([[p.snapshot() for p in flattened_prims]])
                stagenames.append("Expanding Device Agnostic LV2 Prims")


        ################# COMBINE COMPATIBLE PRIMS #################
        flattened_prims = _merge_prims(flattened_prims)

        if debug:#pragma: no cover
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
        if self._fsm is None:
            self._fsm = sm
        assert self._fsm == sm, "Target %s != Actual %s"%\
            (self._fsm.state, sm.state)

        if debug:#pragma: no cover
            stages.append([[p.snapshot() for p in flattened_prims]])
            stagenames.append("Expand to LV1 Primitives")


        if not all((isinstance(p, Executable) for p in flattened_prims)):
            raise ProteusISCError(
                "Reduction did not produce executable instruction sequence.")


        #################### COMBINE LV1 PRIMS #####################

        flattened_prims = _merge_prims(
            flattened_prims,
            stagenames=stagenames, stages=stages,
            debug=self._chain._collect_compiler_merge_artifacts)

        if debug:#pragma: no cover
            stages.append([[p.snapshot() for p in flattened_prims]])
            stagenames.append("Final LV1 merge")

        ############################################################

        if not dryrun:
            self.queue = flattened_prims


    def flush(self):
        """Force the queue of Primitives to compile, execute on the Controller, and fulfill promises with the data returned."""
        self.stages = []
        self.stagenames = []

        if not self.queue:
            return

        if self.print_statistics:#pragma: no cover
            print("LEN OF QUENE", len(self))
            t = time()

        if self._chain._collect_compiler_artifacts:
            self._compile(debug=True, stages=self.stages,
                          stagenames=self.stagenames)
        else:
            self._compile()

        if self.debug:
            print("ABOUT TO EXEC", self.queue)#pragma: no cover

        if self.print_statistics:#pragma: no cover
            print("COMPILE TIME", time()-t)
            print("TOTAL BITS OF ALL PRIMS", sum(
                (p.count for p in self.queue if hasattr(p, 'count'))))
            t = time()

        self._chain._controller._execute_primitives(self.queue)

        if self.print_statistics:
            print("EXECUTE TIME", time()-t)#pragma: no cover

        self.queue = []
        self._chain._sm.state = self._fsm.state

def _merge_prims(prims, *, debug=False, stagenames=None, stages=None):
    """Helper method to greedily combine Frames (of Primitives) or Primitives based on the rules defined in the Primitive's class.

    Used by a CommandQueue during compilation and optimization of
    Primitives.

    Args:
        prims: A list or FrameSequence of Primitives or Frames (respectively) to try to merge together.
        debug: A boolean for if debug information should be generated.
        stages: A list to be edited by this method to store snapshots of the compilation state. Used if debug is True.
        stagenames: A list of strings describing each debug snapshot of the compiilation process. Used if debug is True.

    Returns:
        A list or FrameSequence (the same type as prims) of the compined Primitives or Frames.
    """
    if isinstance(prims, FrameSequence):
        merged_prims = FrameSequence(prims._chain)
    else:
        merged_prims = []
    working_prim = prims[0]
    i = 1
    logging_tmp = []

    while i < len(prims):
        tmp = prims[i]
        res = working_prim.merge(tmp)
        if res is not None:
            working_prim = res
            if debug:#pragma: no cover
                logging_tmp.append(
                    [p.snapshot() for p in
                     merged_prims+[working_prim]])
        else:
            merged_prims.append(working_prim)
            working_prim = tmp
        i += 1
    merged_prims.append(working_prim)
    if debug:#pragma: no cover
        stages.append(logging_tmp)
        stagenames.append("Merge intermediate states")

    return merged_prims
