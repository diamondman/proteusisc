from bitarray import bitarray

from .frame import Frame, FrameSequence
from .primative import Level3Primative, Level2Primative, DeviceTarget,\
    Executable, TDORead

#RunInstruction
#LoadDevDR, LoadDevIR, ReadDevDR, ReadDevIR, LoadReadDevRegister
#ChangeTAPState, LoadReadRegister, ReadDR, LoadDR, LoadIR, Sleep

################### LV3 Primatimes (Dev) ###################

class RunInstruction(Level3Primative, DeviceTarget, TDORead):
    name = "INS_PRIM"

    def __init__(self, device, insname, read=True, execute=True,
                 loop=0, arg=None, delay=0, synthetic=False):
        super(RunInstruction, self).__init__()
        self.insname = insname
        self.read = read
        self.execute = execute
        self.arg = arg
        self.delay = delay
        self.target_device = device
        self._synthetic = synthetic

    @classmethod
    def expand_frame(cls, frame):
        chain = frame._chain
        devs = chain._devices
        seq = FrameSequence(frame._chain,
            Frame(frame._chain, *(LoadDevIR(d,
                    bitarray(d._desc._instructions[frame[i].insname]))
                                  for i, d in enumerate(devs)))
        )

        if frame._valid_prim.arg:
            seq.append(Frame(frame._chain,
                         *(LoadDevDR(d, frame[i].arg)
                          for i, d in enumerate(devs))))

        if frame._valid_prim.execute:
            seq.append(Frame.from_prim(chain,
                    TransitionTAP('TLR')))

        if any((p.delay for p in frame)):
            seq.append(Frame.from_prim(chain,
                    Sleep(max((p.delay for p in frame)))))

        if any((p.read for p in frame)):
            seq.append(Frame(frame._chain,
                        *(ReadDevIR(d,
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
            synthetic=True)
        assert self._group_type == tmp._group_type
        return tmp

################### LV2 Primatimes (Dev) ###################

class LoadDevDR(Level2Primative, DeviceTarget, TDORead):
    _function_name = 'load_dev_dr'
    def __init__(self, dev, data, read=False):
        super(LoadDevDR, self).__init__()
        self.target_device = dev
        self.data = data
        self.read = read

class LoadDevIR(Level2Primative, DeviceTarget):
    _function_name = 'load_dev_ir'
    def __init__(self, dev, data, read=False):
        super(LoadDevIR, self).__init__()
        self.target_device = dev
        self.data = data
        self.read = read

class ReadDevDR(Level2Primative, DeviceTarget):
    _function_name = 'read_dev_dr'
    def __init__(self, dev, bitcount=None):
        super(ReadDevDR, self).__init__()
        self.target_device = dev
        self.bitcount = bitcount

class ReadDevIR(Level2Primative, DeviceTarget):
    _function_name = 'read_dev_ir'
    def __init__(self, dev, bitcount=None):
        super(ReadDevIR, self).__init__()
        self.target_device = dev
        self.bitcount = bitcount






class LoadReadDevRegister(Level2Primative, DeviceTarget):
    _function_name = '_load_dev_register'
    def __init__(self, device, data, read=False, TMSLast=True, bitcount=None, synthetic=False):
        super(LoadReadDevRegister, self).__init__()
        self.target_device = device
        self.data = data
        self.read = read
        self.TMSLast = TMSLast
        self.bitcount=bitcount
        self._synthetic = synthetic

    def get_placeholder_for_dev(self, dev):
        tmp = LoadReadDevRegister(
            dev, data=bitarray(),
            read=False,
            bitcount=self.bitcount,
            TMSLast = self.TMSLast, #This needs to be reviewed
            synthetic=True)
        assert self._group_type == tmp._group_type
        return tmp






################# LV2 Primatimes (No Dev) ##################

class TransitionTAP(Level2Primative):
    _function_name = 'transition_tap'
    def __init__(self, state):
        super(TransitionTAP, self).__init__()
        self.targetstate = state
        self._startstate = None









class LoadReadRegister(Level2Primative):
    _function_name = '_load_register'
    def __init__(self, data, read=False, TMSLast=True, bitcount=None):
        super(LoadReadRegister, self).__init__()
        self.data = data
        self.read = read
        self.TMSLast = TMSLast
        self.bitcount=bitcount

class ReadDR(Level2Primative):
    _function_name = 'read_dr'
    def __init__(self, bitcount):
        super(ReadDR, self).__init__()
        self.bitcount = bitcount

class LoadDR(Level2Primative):
    _function_name = 'load_dr'
    def __init__(self, data, read):
        super(LoadDR, self).__init__()
        self.data = data
        self.read = read

class LoadIR(Level2Primative):
    _function_name = 'load_ir'
    def __init__(self, data, read):
        super(LoadIR, self).__init__()
        self.data = data
        self.read = read

class Sleep(Level2Primative, Executable):
    _function_name = 'sleep'
    _driver_function_name = 'sleep'
    def __init__(self, delay):
        super(Sleep, self).__init__()
        self.delay = delay
