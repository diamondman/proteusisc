from bitarray import bitarray

from .frame import Frame, FrameSequence
from .primitive import Level3Primitive, Level2Primitive, DeviceTarget,\
    Executable, DataRW

#RunInstruction
#LoadDevDR, LoadDevIR, ReadDevDR, ReadDevIR, LoadReadDevRegister
#ChangeTAPState, LoadReadRegister, ReadDR, LoadDR, LoadIR, Sleep

################### LV3 Primatimes (Dev) ###################

class RunInstruction(Level3Primitive, DeviceTarget, DataRW):
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

        load_dev_ir = chain.get_prim('load_dev_ir')
        load_dev_dr = chain.get_prim('load_dev_dr')
        transition_tap = chain.get_prim('transition_tap')
        sleep = chain.get_prim('sleep')
        read_dev_ir = chain.get_prim('read_dev_ir')

        seq = FrameSequence(chain,
            Frame(chain, *(load_dev_ir(dev=d,
                    data=bitarray(d._desc._instructions[frame[i].insname]))
                                  for i, d in enumerate(devs)))
        )

        if frame._valid_prim.data:
            seq.append(Frame(chain,
                         *(load_dev_dr(dev=d, data=frame[i].data)
                          for i, d in enumerate(devs))))

        if frame._valid_prim.execute:
            seq.append(Frame.from_prim(chain, transition_tap('TLR')))

        if any((p.delay for p in frame)):
            seq.append(Frame.from_prim(chain,
                    sleep(max((p.delay for p in frame)))))

        if any((p.read for p in frame)):
            seq.append(Frame(chain,
                        *(read_dev_ir(dev=d, read=frame[i].read,
                            _promise=frame[i]._promise,
                            bitcount=0 if frame[i].read else None)
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

class LoadDevDR(Level2Primitive, DeviceTarget, DataRW):
    _function_name = 'load_dev_dr'

class ReadDevDR(Level2Primitive, DeviceTarget, DataRW):
    _function_name = 'read_dev_dr'
    def __init__(self, bitcount=None, *args, **kwargs):
        super(ReadDevDR, self).__init__(*args, **kwargs)
        self.bitcount = bitcount

    def mergable(self, target):
        if isinstance(target, LoadDevDR):
            if not target.read:
                return True

        return super(ReadDevDR, self).mergable(target)


class LoadDevIR(Level2Primitive, DeviceTarget, DataRW):
    _function_name = 'load_dev_ir'

class ReadDevIR(Level2Primitive, DeviceTarget, DataRW):
    _function_name = 'read_dev_ir'
    def __init__(self, bitcount=None, *args, **kwargs):
        super(ReadDevIR, self).__init__(*args, **kwargs)
        self.bitcount = bitcount

    def mergable(self, target):
        if isinstance(target, LoadDevIR):
            if not target.read:
                return True

        return super(ReadDevIR, self).mergable(target)





class LoadReadDevRegister(Level2Primitive, DeviceTarget, DataRW):
    _function_name = '_load_dev_register'
    def __init__(self, bitcount=None, *args, **kwargs):
        super(LoadReadDevRegister, self).__init__(*args, **kwargs)
        self.bitcount=bitcount

    def get_placeholder_for_dev(self, dev):
        tmp = LoadReadDevRegister(
            dev=dev, data=bitarray(),
            read=False,
            bitcount=self.bitcount,
            _synthetic=True)
        assert self._group_type == tmp._group_type
        return tmp




################# END LV2 Primatimes (Dev) #################

################# LV2 Primatimes (No Dev) ##################

class TransitionTAP(Level2Primitive):
    _function_name = 'transition_tap'
    def __init__(self, state):
        super(TransitionTAP, self).__init__()
        self.targetstate = state
        self._startstate = None

    def mergable(self, target):
        if isinstance(target, TransitionTAP):
            if self.targetstate == target.targetstate:
                return True
        return super(TransitionTAP, self).mergable(target)


class LoadReadRegister(Level2Primitive, DataRW):
    _function_name = '_load_register'
    def __init__(self, bitcount=None, *args, **kwargs):
        super(LoadReadRegister, self).__init__(*args, **kwargs)
        self.bitcount=bitcount

class LoadDR(Level2Primitive, DataRW):
    _function_name = 'load_dr'

class ReadDR(Level2Primitive, DataRW):
    _function_name = 'read_dr'
    def __init__(self, bitcount, *args, **kwargs):
        super(ReadDR, self).__init__(*args, **kwargs)
        self.bitcount = bitcount

    def mergable(self, target):
        if isinstance(target, LoadDR):
            if not target.read:
                return True
        return super(ReadDR, self).mergable(target)


class LoadIR(Level2Primitive, DataRW):
    _function_name = 'load_ir'

class ReadIR(Level2Primitive, DataRW):
    _function_name = 'read_ir'
    def __init__(self, bitcount, *args, **kwargs):
        super(ReadIR, self).__init__(*args, **kwargs)
        self.bitcount = bitcount

    def mergable(self, target):
        if isinstance(target, LoadIR):
            if not target.read:
                return True
        return super(ReadIR, self).mergable(target)

class Sleep(Level2Primitive, Executable):
    _function_name = 'sleep'
    _driver_function_name = 'sleep'
    def __init__(self, delay, *args, **kwargs):
        super(Sleep, self).__init__(*args, **kwargs)
        self.delay = delay

    def mergable(self, target):
        if isinstance(target, Sleep):
            return True
        return super(Sleep, self).mergable(target)


############### END LV2 Primatimes (No Dev) ################
