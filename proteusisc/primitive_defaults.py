import time
from bitarray import bitarray

from .frame import Frame, FrameSequence
from .primitive import Level3Primitive, Level2Primitive, DeviceTarget,\
    Executable, DataRW, ExpandRequiresTAP
from .bittypes import ConstantBitarray, NoCareBitarray
from .contracts import ZERO, ONE, ARBITRARY, CONSTANT, NOCARE
from .promise import TDOPromise, TDOPromiseCollection
from .errors import ProteusISCError

#RunInstruction
#RWDevDR, RWDevIR,
#TransitionTAP, RWDR, RWIR, Sleep

################### LV3 Primatimes (Dev) ###################

class RunInstruction(Level3Primitive, DeviceTarget):
    _function_name = 'run_instruction'
    name = "INS_PRIM"

    def __init__(self, insname, *args, execute=True, read_status=False,
                 loop=0, delay=0, **kwargs):
        super(RunInstruction, self).__init__(*args, **kwargs)
        if (self.data or self.read) and not self.bitcount:
            desc = self.dev._desc
            regname = desc._instruction_register_map[insname]
            self.bitcount = desc._registers[regname]
        if not self.data and self.bitcount:
            self.data = NoCareBitarray(self.bitcount)
        self.read_status = read_status
        self.insname = insname
        self.execute = execute
        self.delay = delay
        self.loop = loop

    @classmethod
    def expand_frame(cls, frame, sm):
        chain = frame._chain
        devs = chain._devices

        rw_dev_ir = chain.get_prim('rw_dev_ir')
        rw_dev_dr = chain.get_prim('rw_dev_dr')
        transition_tap = chain.get_prim('transition_tap')
        sleep = chain.get_prim('sleep')

        seq = FrameSequence(chain,
            Frame(chain, *(
                rw_dev_ir(dev=d, _synthetic=frame[i]._synthetic,
                    _chain=chain,
                    data=bitarray(d._desc._instructions[frame[i].insname])
                ) for i, d in enumerate(devs))))
        sm.state = "UPDATEIR"

        if frame._valid_prim.data:
            seq.append(Frame(chain,
                         *(rw_dev_dr(dev=d, data=frame[i].data,
                                _chain=chain, read=frame[i].read,
                                regname=d._desc._instruction_register_map[frame[i].insname],
                                _promise=frame[i].get_promise()[0],
                                _synthetic=frame[i]._synthetic)
                          for i, d in enumerate(devs))))
            sm.state = "UPDATEDR"

        if frame._valid_prim.execute:
            loop_val = max((p.loop or 0 for p in frame))
            seq.append(Frame.from_prim(chain,
                transition_tap( 'RTI', loop=loop_val, _chain=chain)
            ))
            sm.state = "RTI"

        if any((p.delay for p in frame)):
            seq.append(Frame.from_prim(chain,
                sleep(delay=max((p.delay for p in frame)),
                      _chain=chain)
            ))

        if any((p.read_status for p in frame)):
            seq.append(Frame(chain,
                        *(rw_dev_ir(dev=d, read=frame[i].read_status,
                        _synthetic=frame[i]._synthetic,
                        _promise=frame[i].get_promise()[1],
                        _chain=chain)
                          for i, d in enumerate(devs))))
            sm.state = "UPDATEIR"

        return seq

    @property
    def _group_type(self):
        return (1 if self.execute else 0) +\
            (2 if self.data is not None else 0)

    def get_placeholder_for_dev(self, dev):
        tmp = RunInstruction(_chain=self._chain,
            dev=dev, read=False,
            insname="BYPASS",
            execute=self.execute,
            data=None if self.data == None else NoCareBitarray(1),
            _synthetic=True)
        assert self._group_type == tmp._group_type
        return tmp

    def merge(self, target):
        return None

    def get_promise(self):
        """Return the special set of promises for run_instruction.

        Run Instruction has to support multiple promises (one for
        reading data, and one for reading back the status from IR. All
        other primitives have a single promise, so fitting multiple
        into this system causes some API consistencies.

        This should be reviewed to see if a more coherent alternative
        is available.

        """
        if self._promise is None:
            promise = []
            if self.read:
                promise.append(TDOPromise(self._chain, 0, self.bitcount))
            else:
                promise.append(None)
            if self.read_status:
                promise.append(TDOPromise(self._chain, 0,
                                          self.dev._desc._ir_length))
            else:
                promise.append(None)
            self._promise = promise
        return self._promise

################# END LV3 Primatimes (Dev) #################

################### LV2 Primatimes (Dev) ###################

class RWDevDR(Level2Primitive, DeviceTarget):
    _function_name = 'rw_dev_dr'
    #Complexities arise if people want to get a placeholder. Fix later.
    def __init__(self, *args, regname, **kwargs):
        super(RWDevDR, self).__init__(*args, **kwargs)
        self.bitcount = self.dev._desc._registers[regname]
        if self.data and len(self.data) is not self.bitcount:
            if len(self.data) > self.bitcount:
                raise ValueError("TOO MUCH DATA for IR")
            else:
                self.data = ConstantBitarray(
                    False,
                    (self.bitcount-len(self.data)))+\
                self.data
        if not self.data:
            self.data = ConstantBitarray(False, self.bitcount)

    def merge(self, target):
        return None

    @classmethod
    def expand_frame(cls, frame, sm):
        sm.state = "UPDATEDR"
        chain = frame._chain
        data = NoCareBitarray(0)
        rw_dr = chain.get_prim('rw_dr')
        pframes = []
        for i, p in enumerate(reversed(frame)):
            newprim = rw_dr(read=p.read, data=p.data,
                            _chain=chain, _promise=p._promise,
                            lastbit=i+1 is len(frame))
            pframes.append(Frame.from_prim(chain, newprim))
        return FrameSequence(chain, *pframes)

class RWDevIR(Level2Primitive, DeviceTarget):
    _function_name = 'rw_dev_ir'
    #Complexities arise if people want to get a placeholder. Fix later.
    def __init__(self, *args, **kwargs):
        super(RWDevIR, self).__init__(*args, **kwargs)
        self.bitcount = self.dev._desc._ir_length
        if self.data and len(self.data) is not self.bitcount:
            if len(self.data) > self.bitcount:
                raise ValueError("TOO MUCH DATA for IR")
            else:
                self.data = ConstantBitarray(
                    False,
                    (self.bitcount-len(self.data)))+\
                self.data
        if not self.data:
            self.data = ConstantBitarray(True, self.bitcount)

    def merge(self, target):
        return None

    @classmethod
    def expand_frame(cls, frame, sm):
        sm.state = "UPDATEIR"
        chain = frame._chain

        rw_ir = chain.get_prim('rw_ir')
        pframes = []
        for i, p in enumerate(reversed(frame)):
            data = p.data or ConstantBitarray(True, p.bitcount)
            newprim = rw_ir(read=p.read, data=data,
                            _chain=chain, _promise=p._promise,
                            lastbit=i+1 is len(frame))
            pframes.append(Frame.from_prim(chain, newprim))
        return FrameSequence(chain, *pframes)

    def get_placeholder_for_dev(self, dev):
        tmp = RWDevIR(dev=dev, _chain=self._chain,
                      read=False, _synthetic=True,
                      data=ConstantBitarray(True, dev._desc._ir_length))

        assert self._group_type == tmp._group_type
        return tmp


################# END LV2 Primatimes (Dev) #################

################# LV2 Primatimes (No Dev) ##################

class RWDR(Level2Primitive, DataRW):
    _function_name = 'rw_dr'
    def __init__(self, *args, lastbit=True, **kwargs):
        super(RWDR, self).__init__(*args, **kwargs)
        self.lastbit = lastbit
        if self.data and not self.bitcount:
            self.bitcount = len(self.data)
        if not self.data and self.bitcount:
            self.data = NoCareBitarray(self.bitcount)

    def merge(self, target):
        if isinstance(target, RWDR) and not self.lastbit and \
           target.read is self.read:
            data = NoCareBitarray(0)
            promises = TDOPromiseCollection(self._chain,
                                    len(self.data)+len(target.data))
            for p in (target, self):
                promises.add(p._promise, len(data))
                data += p.data

            return RWDR(data=data, read=self.read,
                        _promise=promises if promises else None,
                        _chain=self._chain, lastbit=target.lastbit)
        return None

    def expand(self, chain, sm):
        prims = []
        if sm.state != "SHIFTDR":
            prims.append(chain.get_prim('transition_tap')
                         ('SHIFTDR',  _chain=chain))
            sm.state = "SHIFTDR"

        prims.append(
            chain.get_prim('rw_reg')(data=self.data, read=self.read,
                                _promise=self._promise, _chain=chain,
                                lastbit=self.lastbit))
        if self.lastbit:
            prims.append(chain.get_prim('transition_tap')
                         ('UPDATEDR',  _chain=chain))
            sm.state = "UPDATEDR"

        return prims

class RWIR(Level2Primitive, DataRW):
    _function_name = 'rw_ir'
    def __init__(self, *args, lastbit=True, **kwargs):
        super(RWIR, self).__init__(*args, **kwargs)
        self.lastbit = lastbit
        if self.data and not self.bitcount:
            self.bitcount = len(self.data)
        if not self.data and self.bitcount:
            self.data = ConstantBitarray(True, self.bitcount)

    def merge(self, target):
        if isinstance(target, RWIR) and not self.lastbit and \
           target.read is self.read:
            data = NoCareBitarray(0)
            promises = TDOPromiseCollection(self._chain,
                                len(self.data)+len(target.data))
            for p in (target, self):
                promises.add(p._promise, len(data))
                data += p.data

            return RWIR(data=data, read=self.read,
                        _promise=promises if promises else None,
                        _chain=self._chain, lastbit=target.lastbit)
        return None

    def expand(self, chain, sm):
        prims = []

        if sm.state != "SHIFTIR":
            prims.append(chain.get_prim('transition_tap')
                         ('SHIFTIR', _chain=chain))
            sm.state = "SHIFTIR"
            prims[0].oldstate = sm.state

        prims.append(
            chain.get_prim('rw_reg')(read=self.read, data=self.data,
                                     _promise=self._promise, _chain=chain,
                                     lastbit=self.lastbit))
        if self.lastbit:
            prims.append(chain.get_prim('transition_tap')
                         ('UPDATEIR',  _chain=chain))
            sm.state = "UPDATEIR"

        return prims

class RWReg(Level2Primitive, DataRW, ExpandRequiresTAP):
    _function_name = 'rw_reg'
    def __init__(self, *args, lastbit=True, **kwargs):
        super(RWReg, self).__init__(*args, **kwargs)
        self.lastbit = lastbit
        if self.data and not self.bitcount:
            self.bitcount = len(self.data)
        if not self.data and self.bitcount:
            self.data = NoCareBitarray(self.bitcount)

    def merge(self, target):
        return None

    def expand(self, chain, sm):
        if sm.state not in {"SHIFTIR", "SHIFTDR"}:
            raise ProteusISCError("Invalid State. RWReg Requires state "
                                  "to be SHIFTIR or SHIFTDR. This "
                                  "is caused by not proceeding RWReg "
                                  "with a tap transition.")
        data = self.data
        res = []

        if not self.lastbit:
            # pylint: disable=no-member
            reqef = (
                ZERO, #TMS
                NOCARE if isinstance(data, NoCareBitarray) else
                    (ONE if data._val else ZERO)
                        if isinstance(data, ConstantBitarray) else
                    ARBITRARY, #TDI
                ONE if self.read else NOCARE #TDO
            )
            write_data = self._chain.get_fitted_lv1_prim(reqef)
            res.append(write_data(tms=False, tdi=data,
                                  tdo=self.read or None,
                                  _promise=self._promise))
        else:
            sm.transition_bit(True)
            if self._promise:
                rest, tail = self._promise.split_to_subpromises()
            else:
                rest, tail = None, None

            if len(data)>1:
                # pylint: disable=no-member
                reqef = (
                    ZERO, #TMS
                    NOCARE if isinstance(data, NoCareBitarray) else
                        (ONE if data._val else ZERO)
                            if isinstance(data, ConstantBitarray) else
                        ARBITRARY, #TDI
                    ONE if self.read else NOCARE #TDO
                )
                write_data = self._chain.get_fitted_lv1_prim(reqef)
                res.append(write_data(tms=False, tdi=data[1:],
                                      tdo=self.read or None,
                                      _promise=rest))

            reqef = (
                ONE, #TMS
                ONE if data[0] else ZERO, #TDI
                ONE if self.read else NOCARE #TDO
            )
            if self.debug:
                print(('  \033[95m%s %s %s\033[94m'%tuple(reqef)),self,'\033[0m')
            write_last = self._chain.get_fitted_lv1_prim(reqef)
            res.append(write_last(tms=True, tdi=data[0],
                                  tdo=self.read or None, _promise=tail))

        return res

class TransitionTAP(Level2Primitive, ExpandRequiresTAP):
    _function_name = 'transition_tap'
    def __init__(self, state, *args, loop=None, **kwargs):
        super(TransitionTAP, self).__init__(*args, **kwargs)
        self.state = state
        self.loop = loop
        if loop and state not in ("RTI", "TLR", "SHIFTDR", "SHIFTIR"):
            raise ProteusISCError("Invalid State. Looping the TAP state "
                                  "is only supported in the SHIFTIR, "
                                  "SHIFTDR, TLR, or RTI states.")


    def merge(self, target):
        if isinstance(target, TransitionTAP):
            if self.state == target.state:
                if target.loop and not self.loop:
                    return target
                elif target.loop:
                    return TransitionTAP(self.state,
                                         self.loop+target.loop)
                else:
                    return self
        return None

    def apply_tap_effect(self, sm):
        sm.state = self.state

    def expand(self, chain, sm):
        data = sm.calc_transition_to_state(self.state)
        sm.state = self.state

        if all(data):
            data = ConstantBitarray(True, len(data))
        elif not any(data):
            data = ConstantBitarray(False, len(data))

        if self.loop:
            if self.state == "TLR":
                bit = True
            elif self.state in ("RTI", "SHIFTDR", "SHIFTIR"):
                bit = False
            else:
                raise ProteusISCError(
                    "Invalid State. Looping the TAP state "
                    "is only supported in the SHIFTIR, "
                    "SHIFTDR, TLR, or RTI states.")
            data = ConstantBitarray(bit, self.loop) + data

        reqef = (
            NOCARE if isinstance(data, NoCareBitarray) else
                (ONE if data._val else ZERO)
                    if isinstance(data, ConstantBitarray) else
                ARBITRARY, #TMS
            NOCARE, NOCARE #TDI, TDO
        )
        if self.debug:
            print(('  \033[95m%s %s %s\033[94m'%tuple(reqef)),self,'\033[0m')
        best_prim = self._chain.get_fitted_lv1_prim(reqef)

        return [
            best_prim(tms=data)
        ]

class Sleep(Level2Primitive, Executable):
    _function_name = 'sleep'
    #_driver_function_name = 'sleep'
    def __init__(self, *args, delay, **kwargs):
        super(Sleep, self).__init__(*args, **kwargs)
        self.delay = delay

    def merge(self, target):
        if isinstance(target, Sleep):
            return Sleep(delay=self.delay+target.delay,
                         _chain=self._chain)
        return None

    def expand(self, chain, sm):
        return None

    def execute(self):
        time.sleep(self.delay/1000)

############### END LV2 Primatimes (No Dev) ################
