from bitarray import bitarray

from .frame import Frame, FrameSequence
from .primative import Level3Primative, Level2Primative, DeviceTarget,\
    Executable, TDORead

################### LV3 Primatimes (Dev) ###################

class RunInstructionPrimative(Level3Primative, DeviceTarget, TDORead):
    name = "INS_PRIM"

    def __init__(self, device, insname, read=True, execute=True,
                 loop=0, arg=None, delay=0, synthetic=False):
        super(RunInstructionPrimative, self).__init__()
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
            Frame(frame._chain, *(LoadDevIRPrimative(d,
                    bitarray(d._desc._instructions[frame[i].insname]))
                                  for i, d in enumerate(devs)))
        )

        if frame._valid_prim.arg:
            seq.append(Frame(frame._chain,
                         *(LoadDevDRPrimative(d, frame[i].arg)
                          for i, d in enumerate(devs))))

        if frame._valid_prim.execute:
            seq.append(Frame.from_prim(chain,
                    ChangeTAPStatePrimative('TLR')))

        if any((p.delay for p in frame)):
            seq.append(Frame.from_prim(chain,
                    SleepPrimative(max((p.delay for p in frame)))))

        if any((p.read for p in frame)):
            seq.append(Frame(frame._chain,
                        *(ReadDevIRPrimative(d,
                            bitcount=0 if frame[i].read else None)
                          for i, d in enumerate(devs))))

        return seq

    def __repr__(self):
        n = getattr(self, '_function_name', None) or \
            getattr(type(self), 'name', None) or \
            type(self).__name__
        return "<%s(D:%s;exe:%s)>"\
            %(n, self.target_device.chain_index, self.execute)

    def compatible(self, *target):
        return all((self.signature() == t.signature() for t in target))

    @property
    def _group_type(self):
        return (1 if self.execute else 0) +\
            (2 if self.arg is not None else 0)

    def get_placeholder_for_dev(self, dev):
        tmp = RunInstructionPrimative(
            dev, read=False,
            insname="BYPASS",
            execute=self.execute,
            arg=None if self.arg == None else bitarray(),
            synthetic=True)
        assert self._group_type == tmp._group_type
        return tmp

################### LV2 Primatimes (Dev) ###################

class LoadDevDRPrimative(Level2Primative, DeviceTarget, TDORead):
    _function_name = 'load_dev_dr'
    _is_macro = True
    def __init__(self, dev, data, read=False):
        super(LoadDevDRPrimative, self).__init__()
        self.target_device = dev
        self.data = data
        self.read = read

    def _expand_macro(self, command_queue):
        return [command_queue.sc._lv2_primatives.get('transition_tap')\
                ("SHIFTDR"),
                command_queue.sc._lv2_primatives.get('_load_register')\
                (self.data, read=self.read)]

    @classmethod
    def expand_frame(cls, frame):
        return [frame]

    @property
    def _group_type(self):
        return 0

    def __repr__(self):
        return "<LoadDevDR(D:%s;%s bits; %sRead)>"%(
            self.target_device.chain_index,
            len(self.data),
            '' if self.read else 'No ')


class LoadDevIRPrimative(Level2Primative, DeviceTarget):
    _function_name = 'load_dev_ir'
    _is_macro = True
    def __init__(self, dev, data, read=False):
        super(LoadDevIRPrimative, self).__init__()
        self.target_device = dev
        self.data = data
        self.read = read

    def _expand_macro(self, command_queue):
        return [command_queue.sc._lv2_primatives.get('transition_tap')("SHIFTIR"),
                command_queue.sc._lv2_primatives.get('_load_register')(self.data, read=self.read)]

    @classmethod
    def expand_frame(cls, frame):
        return [frame]

    @property
    def _group_type(self):
        return 0

    def __repr__(self):
        return "<LoadDevIR(D:%s;%s bits; %sRead)>"%(
            self.target_device.chain_index,
            len(self.data),
            '' if self.read else 'No ')

class ReadDevDRPrimative(Level2Primative, DeviceTarget):
    _function_name = 'read_dev_dr'
    def __init__(self, dev, bitcount=None):
        super(ReadDevDRPrimative, self).__init__()
        self.target_device = dev
        self.bitcount = bitcount

    @classmethod
    def expand_frame(cls, frame):
        return [frame]

    @property
    def _group_type(self):
        return 0

    def __repr__(self):
        return "<ReadDevDR(D:%s;%s bits; %sRead)>"%(
            self.target_device.chain_index,
            len(self.data),
            '' if self.read else 'No ')


class ReadDevIRPrimative(Level2Primative, DeviceTarget):
    _function_name = 'read_dev_ir'
    def __init__(self, dev, bitcount=None):
        super(ReadDevIRPrimative, self).__init__()
        self.target_device = dev
        self.bitcount = bitcount

    @classmethod
    def expand_frame(cls, frame):
        return [frame]

    @property
    def _group_type(self):
        return 0

    def __repr__(self):
        return "<ReadDevIR(D:%s;%s bits)>"%\
            (self.target_device.chain_index, self.bitcount)






class LoadReadDevRegisterPrimative(Level2Primative, DeviceTarget):
    _function_name = '_load_dev_register'
    def __init__(self, device, data, read=False, TMSLast=True, bitcount=None, synthetic=False):
        super(LoadReadDevRegisterPrimative, self).__init__()
        self.target_device = device
        self.data = data
        self.read = read
        self.TMSLast = TMSLast
        self.bitcount=bitcount
        self._synthetic = synthetic

    @property
    def _group_type(self):
        return 0

    def __repr__(self):
        n = getattr(self, '_function_name', None) or \
            getattr(type(self), 'name', None) or \
            type(self).__name__
        return "<%s(D:%s)>"%(n, self.target_device.chain_index)

    def get_placeholder_for_dev(self, dev):
        tmp = LoadReadDevRegisterPrimative(
            dev, data=bitarray(),
            read=False,
            bitcount=self.bitcount,
            TMSLast = self.TMSLast, #This needs to be reviewed
            synthetic=True)
        assert self._group_type == tmp._group_type
        return tmp












################# LV2 Primatimes (No Dev) ##################

class ChangeTAPStatePrimative(Level2Primative):
    _function_name = 'transition_tap'
    def __init__(self, state):
        super(ChangeTAPStatePrimative, self).__init__()
        self.targetstate = state
        self._startstate = None

    def __repr__(self):
        return "<TAPTransition(%s=>%s)>"%(self._startstate if self._startstate
                                          else '?', self.targetstate)

    @classmethod
    def expand_frame(cls, frame):
        return [frame]

    @property
    def _group_type(self):
        return 0











class ChangeTAPStatePrimative2(Level2Primative):
    _function_name = 'transition_tap'
    def __init__(self, state):
        super(ChangeTAPStatePrimative, self).__init__()
        self.targetstate = state
        self._startstate = None

    def _stage(self, fsm_state):
        super(ChangeTAPStatePrimative, self)._stage(fsm_state)
        self._startstate = fsm_state
        return self.targetstate != fsm_state

    def _commit(self, command_queue):
        super(ChangeTAPStatePrimative, self)._commit(command_queue)
        self._bits = command_queue._fsm.calc_transition_to_state(self.targetstate)
        command_queue._fsm.state = self.targetstate
        return False

    @property
    def required_effect(self):
        if not self._staged:
            raise Exception("required_effect is only available after staging")
        return [SEQUENCE,
                ZERO,
                DOESNOTMATTER]

    def get_effect_bits(self):
        return [len(self._bits), self._bits, 0, 0]

    def __repr__(self):
        return "<TAPTransition(%s=>%s)>"%(self._startstate if self._startstate
                                          else '?', self.targetstate)


class LoadReadRegisterPrimative(Level2Primative):
    _function_name = '_load_register'
    def __init__(self, data, read=False, TMSLast=True, bitcount=None):
        super(LoadReadRegisterPrimative, self).__init__()
        self.data = data
        self.read = read
        self.TMSLast = TMSLast
        self.bitcount=bitcount

    @property
    def _group_type(self):
        return 0

    def _stage(self, fsm_state):
        super(LoadReadRegisterPrimative, self)._stage(fsm_state)
        if fsm_state not in ["SHIFTIR", "SHIFTDR"]:
            return False

        if not ((self.bitcount if self.bitcount else len(self.data))>0):
            return False
        return True

    def _commit(self, command_queue):
        super(LoadReadRegisterPrimative, self)._commit(command_queue)
        if self.TMSLast:
            command_queue._fsm.transition_bit(1)
        return self.read

    @property
    def required_effect(self):
        if not self._staged:
            raise Exception("required_effect is only available after staging")
        return [SEQUENCE if self.TMSLast else ZERO,
                CONSTANT if self.bitcount else SEQUENCE,
                ONE if self.read else DOESNOTMATTER] #TMS TDI TDO

    def get_effect_bits(self):
        TMS = 0
        if self.TMSLast:
            TMS = bitarray("1"+(len(self.data)-1)*'0')
        return [self.bitcount if self.bitcount else len(self.data),
                TMS, #TMS
                self.data, #TDI
                self.read] #TDO

    def __repr__(self):
        return "<LOAD/READREGISTER(%s bits, %sRead)>"%(
            self.bitcount if self.bitcount else len(self.data),
            '' if self.read else 'No')

    @property
    def _group_type(self):
        return 0


class ReadDRPrimative(Level2Primative):
    _function_name = 'read_dr'
    _is_macro = True
    def __init__(self, bitcount):
        super(ReadDRPrimative, self).__init__()
        self.bitcount = bitcount

    def _expand_macro(self, command_queue):
        return [command_queue.sc._lv2_primatives.get('transition_tap')("SHIFTDR"),
                command_queue.sc._lv2_primatives.get('_load_register')(
                    False, read=True, TMSLast=False, bitcount=self.bitcount)]

    @property
    def _group_type(self):
        return 0

    def __repr__(self):
        return "<ReadDR(%s bits)>"%(len(self.data))

class LoadDRPrimative(Level2Primative):
    _function_name = 'load_dr'
    _is_macro = True
    def __init__(self, data, read):
        super(LoadDRPrimative, self).__init__()
        self.data = data
        self.read = read

    def _expand_macro(self, command_queue):
        return [command_queue.sc._lv2_primatives.get('transition_tap')("SHIFTDR"),
                command_queue.sc._lv2_primatives.get('_load_register')(self.data, read=self.read)]

    @property
    def _group_type(self):
        return 0

    def __repr__(self):
        return "<LoadDR(%s bits, %sRead)>"%(len(self.data),
                                            '' if self.read else 'No')

class LoadIRPrimative(Level2Primative):
    _function_name = 'load_ir'
    _is_macro = True
    def __init__(self, data, read):
        super(LoadIRPrimative, self).__init__()
        self.data = data
        self.read = read

    def _expand_macro(self, command_queue):
        return [command_queue.sc._lv2_primatives.get('transition_tap')("SHIFTIR"),
                command_queue.sc._lv2_primatives.get('_load_register')(self.data, read=self.read)]

    @property
    def _group_type(self):
        return 0

    def __repr__(self):
        return "<LoadIR(%s bits, %sRead)>"%(len(self.data),
                                            '' if self.read else 'No')

class SleepPrimative(Level2Primative, Executable):
    _function_name = 'sleep'
    _driver_function_name = 'sleep'
    def __init__(self, delay):
        super(SleepPrimative, self).__init__()
        self.delay = delay

    def _stage(self, fsm_state):
        super(SleepPrimative, self)._stage(fsm_state)
        return self.delay>0

    def _get_args(self):
        return [self.delay], {}

    def __repr__(self):
        return "<SLEEP(%s seconds)>"%(self.delay)

    @property
    def _group_type(self):
        return 0
