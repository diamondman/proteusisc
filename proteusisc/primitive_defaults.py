import time
from bitarray import bitarray

from .frame import Frame, FrameSequence
from .primitive import Level3Primitive, Level2Primitive, DeviceTarget,\
    Executable, DataRW, ExpandRequiresTAP, ZERO, ONE, ARBITRARY, \
    CONSTANT, NOCARE,\
    ConstantBitarray, NoCareBitarray
from .promise import TDOPromise
from .errors import ProteusISCError

#RunInstruction
#RWDevDR, RWDevIR,
#TransitionTAP, RWDR, RWIR, Sleep

################### LV3 Primatimes (Dev) ###################

class RunInstruction(Level3Primitive, DeviceTarget):
    _function_name = 'run_instruction'
    name = "INS_PRIM"

    def __init__(self, insname, execute=True,
                 loop=0, delay=0, *args, **kwargs):
        super(RunInstruction, self).__init__(*args, **kwargs)
        self.bitcount = self.dev._desc._ir_length
        self.insname = insname
        self.execute = execute
        self.delay = delay

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
        sm.state = "EXIT1IR"

        if frame._valid_prim.data:
            seq.append(Frame(chain,
                         *(rw_dev_dr(dev=d, data=frame[i].data,
                                _chain=chain,
                                regname=d._desc._instruction_register_map[frame[i].insname],
                                _synthetic=frame[i]._synthetic)
                          for i, d in enumerate(devs))))
            sm.state = "EXIT1DR"

        if frame._valid_prim.execute:
            seq.append(Frame.from_prim(chain,
                transition_tap( 'TLR', _chain=chain)
            ))
            sm.state = "TLR"

        if any((p.delay for p in frame)):
            seq.append(Frame.from_prim(chain,
                sleep(delay=max((p.delay for p in frame)),
                      _chain=chain)
            ))

        if any((p.read for p in frame)):
            seq.append(Frame(chain,
                        *(rw_dev_ir(dev=d, read=frame[i].read,
                        _synthetic=frame[i]._synthetic,
                        _promise=frame[i]._promise,
                        _chain=chain)
                          for i, d in enumerate(devs))))
            sm.state = "EXIT1IR"

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

    @classmethod
    def expand_frame(cls, frame, sm):
        sm.state = "EXIT1DR"
        chain = frame._chain
        data = NoCareBitarray(0)
        promises = []#p._promise for p in frame if p._promise]
        for p in reversed(frame):
            if p._promise:
                promise = TDOPromise(chain,
                                     p._promise._bitstart + len(data),
                                     p._promise._bitlength)
                promises.append(promise)
            if p.data:
                data += p.data[::-1]
            else:
                data += ConstantBitarray(False, p.bitcount)
        return FrameSequence(chain,
            Frame.from_prim(chain,
                chain.get_prim('rw_dr')
                            (read=frame._valid_prim.read,
                             data=data[::-1], _chain=chain,
                             _promise=promises))
            )

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

    @classmethod
    def expand_frame(cls, frame, sm):
        sm.state = "EXIT1IR"
        chain = frame._chain
        data = NoCareBitarray(0)
        promises = []
        for p in reversed(frame):
            if p._promise:
                promise = TDOPromise(chain,
                                     p._promise._bitstart + len(data),
                                     p._promise._bitlength)
                promises.append(promise)
            if p.data:
                data += p.data[::-1]
            else:
                data += ConstantBitarray(True, p.bitcount)

        return FrameSequence(chain,
            Frame.from_prim(chain,
                chain.get_prim('rw_ir')
                            (read=frame._valid_prim.read,
                             data=data[::-1], _chain=chain,
                             _promise=promises))
            )

        return seq

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
    def merge(self, target):
        return None

    def expand(self, chain, sm):
        sm.state = "EXIT1DR"
        return [
            chain.get_prim('transition_tap')('SHIFTDR',  _chain=chain),
            chain.get_prim('rw_reg')(read=self.read, data=self.data,
                                     _promise=self._promise, _chain=chain)
        ]

class RWIR(Level2Primitive, DataRW):
    _function_name = 'rw_ir'
    def merge(self, target):
        return None

    def expand(self, chain, sm):
        sm.state = "EXIT1IR"
        return [
            chain.get_prim('transition_tap')('SHIFTIR', _chain=chain,),
            chain.get_prim('rw_reg')(read=self.read, data=self.data,
                                     _promise=self._promise, _chain=chain)
        ]

class RWReg(Level2Primitive, DataRW, ExpandRequiresTAP):
    _function_name = 'rw_reg'

    def merge(self, target):
        return None

    def expand(self, chain, sm):
        if sm.state not in {"SHIFTIR", "SHIFTDR"}:
            raise ProteusISCError("Invalid State. RWReg Requires state "
                                  "to be SHIFTIR or SHIFTDR. This "
                                  "is caused by not proceeding RWReg "
                                  "with a tap transition.")
        sm.transition_bit(True)

        data = self.data
        res = []

        if self._promise:
            if isinstance(self._promise, list):
                other_promises = self._promise[:-1]
                last_promise = self._promise[-1]
            else:
                other_promises = []
                last_promise = self._promise

        if len(data)>1:
            reqef = (
                ZERO, #TMS
                #ONE if all(data[:-1]) else (ZERO if not any(data[:-1])
                #                            else ARBITRARY), #TDI
                NOCARE if isinstance(data, NoCareBitarray) else
                    (ONE if data._val else ZERO)
                        if isinstance(data, ConstantBitarray) else
                    ARBITRARY, #TDI
                ONE if self.read else NOCARE #TDO
            )
            pro = None
            if self._promise:
                pro = TDOPromise(chain, 0, 0)
                last_promise._addsub(pro)
            write_data = self._chain.get_fitted_lv1_prim(reqef)
            res.append(write_data(tms=False, tdi=data[1:],
                                  tdo=self.read or None, _promise=pro))

        reqef = (
            ONE, #TMS
            ONE if data[-1] else ZERO, #TDI
            ONE if self.read else NOCARE #TDO
        )
        print(('  \033[95m%s %s %s\033[94m'%tuple(reqef)),self,'\033[0m')

        pro = None
        if self._promise:
            pro = TDOPromise(chain, 0, 0)
            last_promise._addsub(pro)
        write_last = self._chain.get_fitted_lv1_prim(reqef)
        res.append(write_last(tms=True, tdi=data[0],
                              tdo=self.read or None, _promise=pro))

        return res

class TransitionTAP(Level2Primitive, ExpandRequiresTAP):
    _function_name = 'transition_tap'
    def __init__(self, state, *args, **kwargs):
        super(TransitionTAP, self).__init__(*args, **kwargs)
        self.state = state

    def merge(self, target):
        if isinstance(target, TransitionTAP):
            if self.state == target.state:
                return self
        return None

    def expand(self, chain, sm):
        data = sm.calc_transition_to_state(self.state)
        sm.state = self.state

        reqef = (ONE if all(data) else
                 (ZERO if not any(data) else ARBITRARY),
                 NOCARE, NOCARE)
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
