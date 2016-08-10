from bitarray import bitarray

from .frame import Frame, FrameSequence
from .primitive import Level3Primitive, Level2Primitive, DeviceTarget,\
    Executable, DataRW

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
        self.insname = insname
        self.execute = execute
        self.delay = delay

    @classmethod
    def expand_frame(cls, frame):
        chain = frame._chain
        devs = chain._devices

        rw_dev_ir = chain.get_prim('rw_dev_ir')
        rw_dev_dr = chain.get_prim('rw_dev_dr')
        transition_tap = chain.get_prim('transition_tap')
        sleep = chain.get_prim('sleep')

        seq = FrameSequence(chain,
            Frame(chain, *(
                rw_dev_ir(dev=d, _synthetic=frame[i]._synthetic,
                    data=bitarray(d._desc._instructions[frame[i].insname])
                ) for i, d in enumerate(devs))))

        if frame._valid_prim.data:
            seq.append(Frame(chain,
                         *(rw_dev_dr(dev=d, data=frame[i].data,
                                regname=d._desc._instruction_register_map[frame[i].insname],
                                _synthetic=frame[i]._synthetic)
                          for i, d in enumerate(devs))))

        if frame._valid_prim.execute:
            seq.append(Frame.from_prim(chain,
                transition_tap('TLR')
            ))

        if any((p.delay for p in frame)):
            seq.append(Frame.from_prim(chain,
                sleep(delay=max((p.delay for p in frame)))
            ))

        if any((p.read for p in frame)):
            seq.append(Frame(chain,
                        *(rw_dev_ir(dev=d, read=frame[i].read,
                        _synthetic=frame[i]._synthetic,
                        _promise=frame[i]._promise)
                          for i, d in enumerate(devs))))

        return seq

    @property
    def _group_type(self):
        return (1 if self.execute else 0) +\
            (2 if self.data is not None else 0)

    def get_placeholder_for_dev(self, dev):
        tmp = RunInstruction(
            dev=dev, read=False,
            insname="BYPASS",
            execute=self.execute,
            data=None if self.data == None else bitarray(),
            _synthetic=True)
        assert self._group_type == tmp._group_type
        return tmp

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
                self.data = bitarray('0'*(self.bitcount-len(self.data)))\
                            +self.data

    @classmethod
    def expand_frame(cls, frame):
        chain = frame._chain
        data = bitarray()
        for p in reversed(frame):
            if p.data:
                data += p.data
            else:
                data += bitarray('0'*p.bitcount)
        return FrameSequence(chain,
            Frame.from_prim(chain,
                chain.get_prim('transition_tap')('SHIFTDR')
            ),
            Frame.from_prim(chain,
                chain.get_prim('rw_dr')(read=frame._valid_prim.read,
                                        data=data))
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
                self.data = bitarray('0'*(self.bitcount-len(self.data)))\
                            +self.data

    @classmethod
    def expand_frame(cls, frame):
        chain = frame._chain
        data = bitarray()
        for p in reversed(frame):
            if p.data:
                data += p.data
            else:
                data += bitarray('1'*p.bitcount)
        return FrameSequence(chain,
            Frame.from_prim(chain,
                chain.get_prim('transition_tap')('SHIFTIR')
            ),
            Frame.from_prim(chain,
                chain.get_prim('rw_ir')(read=frame._valid_prim.read,
                                        data=data))
            )

        return seq


################# END LV2 Primatimes (Dev) #################

################# LV2 Primatimes (No Dev) ##################

class RWDR(Level2Primitive, DataRW):
    _function_name = 'rw_dr'

class RWIR(Level2Primitive, DataRW):
    _function_name = 'rw_ir'

class TransitionTAP(Level2Primitive):
    _function_name = 'transition_tap'
    def __init__(self, state, *args, **kwargs):
        super(TransitionTAP, self).__init__(*args, **kwargs)
        self.targetstate = state
        self._startstate = None

    def merge(self, target):
        if isinstance(target, TransitionTAP):
            if self.targetstate == target.targetstate:
                return self
        return None

class Sleep(Level2Primitive, Executable):
    _function_name = 'sleep'
    _driver_function_name = 'sleep'
    def __init__(self, *args, delay, **kwargs):
        super(Sleep, self).__init__(*args, **kwargs)
        self.delay = delay

    def merge(self, target):
        if isinstance(target, Sleep):
            return Sleep(delay=self.delay+target.delay)
        return None


############### END LV2 Primatimes (No Dev) ################
