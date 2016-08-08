from bitarray import bitarray

from .frame import Frame, FrameSequence
from .primitive import Level3Primitive, Level2Primitive, DeviceTarget,\
    Executable, TDORead

#RunInstruction
#LoadDevDR, LoadDevIR, ReadDevDR, ReadDevIR, LoadReadDevRegister
#ChangeTAPState, LoadReadRegister, ReadDR, LoadDR, LoadIR, Sleep

################### LV3 Primatimes (Dev) ###################

class RunInstruction(Level3Primitive, DeviceTarget, TDORead):
    _function_name = 'run_instruction'
    name = "INS_PRIM"

    def __init__(self, device, insname, execute=True,
                 loop=0, arg=None, delay=0, *args, **kwargs):
        super(RunInstruction, self).__init__(*args, **kwargs)
        self.insname = insname
        self.execute = execute
        self.arg = arg
        self.delay = delay
        self.target_device = device

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
            Frame(chain, *(load_dev_ir(d,
                    bitarray(d._desc._instructions[frame[i].insname]))
                                  for i, d in enumerate(devs)))
        )

        if frame._valid_prim.arg:
            seq.append(Frame(chain,
                         *(load_dev_dr(d, frame[i].arg)
                          for i, d in enumerate(devs))))

        if frame._valid_prim.execute:
            seq.append(Frame.from_prim(chain, transition_tap('TLR')))

        if any((p.delay for p in frame)):
            seq.append(Frame.from_prim(chain,
                    sleep(max((p.delay for p in frame)))))

        if any((p.read for p in frame)):
            seq.append(Frame(chain,
                        *(read_dev_ir(d, read=frame[i].read,
                            _promise=frame[i]._promise,
                            bitcount=0 if frame[i].read else None)
                          for i, d in enumerate(devs))))

        return seq

    @property
    def _group_type(self):
        return (1 if self.execute else 0) +\
            (2 if self.arg is not None else 0)

    def get_placeholder_for_dev(self, dev):
        tmp = RunInstruction(
            dev, read=False,
            insname="BYPASS",
            execute=self.execute,
            arg=None if self.arg == None else bitarray(),
            _synthetic=True)
        assert self._group_type == tmp._group_type
        return tmp

################# END LV3 Primatimes (Dev) #################

################### LV2 Primatimes (Dev) ###################

class LoadDevDR(Level2Primitive, DeviceTarget, TDORead):
    _function_name = 'load_dev_dr'
    def __init__(self, dev, data, *args, **kwargs):
        super(LoadDevDR, self).__init__(*args, **kwargs)
        self.target_device = dev
        self.data = data

class LoadDevIR(Level2Primitive, DeviceTarget, TDORead):
    _function_name = 'load_dev_ir'
    def __init__(self, dev, data, *args, **kwargs):
        super(LoadDevIR, self).__init__(*args, **kwargs)
        self.target_device = dev
        self.data = data

class ReadDevDR(Level2Primitive, DeviceTarget, TDORead):
    _function_name = 'read_dev_dr'
    def __init__(self, dev, bitcount=None, *args, **kwargs):
        super(ReadDevDR, self).__init__(*args, **kwargs)
        self.target_device = dev
        self.bitcount = bitcount

class ReadDevIR(Level2Primitive, DeviceTarget, TDORead):
    _function_name = 'read_dev_ir'
    def __init__(self, dev, bitcount=None, *args, **kwargs):
        super(ReadDevIR, self).__init__(*args, **kwargs)
        self.target_device = dev
        self.bitcount = bitcount






class LoadReadDevRegister(Level2Primitive, DeviceTarget, TDORead):
    _function_name = '_load_dev_register'
    def __init__(self, device, data, TMSLast=True,
                 bitcount=None, *args, **kwargs):
        super(LoadReadDevRegister, self).__init__(*args, **kwargs)
        self.target_device = device
        self.data = data
        self.TMSLast = TMSLast
        self.bitcount=bitcount

    def get_placeholder_for_dev(self, dev):
        tmp = LoadReadDevRegister(
            dev, data=bitarray(),
            read=False,
            bitcount=self.bitcount,
            TMSLast = self.TMSLast, #This needs to be reviewed
            _synthetic=True)
        assert self._group_type == tmp._group_type
        return tmp






################# LV2 Primatimes (No Dev) ##################

class TransitionTAP(Level2Primitive):
    _function_name = 'transition_tap'
    def __init__(self, state):
        super(TransitionTAP, self).__init__()
        self.targetstate = state
        self._startstate = None

class LoadReadRegister(Level2Primitive, TDORead):
    _function_name = '_load_register'
    def __init__(self, data, TMSLast=True, bitcount=None, *args, **kwargs):
        super(LoadReadRegister, self).__init__(*args, **kwargs)
        self.data = data
        self.TMSLast = TMSLast
        self.bitcount=bitcount

class LoadDR(Level2Primitive, TDORead):
    _function_name = 'load_dr'
    def __init__(self, data, *args, **kwargs):
        super(LoadDR, self).__init__(*args, **kwargs)
        self.data = data

class ReadDR(Level2Primitive, TDORead):
    _function_name = 'read_dr'
    def __init__(self, bitcount, *args, **kwargs):
        super(ReadDR, self).__init__(*args, **kwargs)
        self.bitcount = bitcount

class LoadIR(Level2Primitive, TDORead):
    _function_name = 'load_ir'
    def __init__(self, data, *args, **kwargs):
        super(LoadIR, self).__init__(*args, **kwargs)
        self.data = data

class ReadIR(Level2Primitive, TDORead):
    _function_name = 'read_ir'
    def __init__(self, bitcount, *args, **kwargs):
        super(ReadIR, self).__init__(*args, **kwargs)
        self.bitcount = bitcount

class Sleep(Level2Primitive, Executable):
    _function_name = 'sleep'
    _driver_function_name = 'sleep'
    def __init__(self, delay, *args, **kwargs):
        super(Sleep, self).__init__(*args, **kwargs)
        self.delay = delay
