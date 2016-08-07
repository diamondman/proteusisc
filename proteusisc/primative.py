from bitarray import bitarray
import types

DOESNOTMATTER = 0
ZERO = 1
ONE = 2
CONSTANT = ZERO|ONE
SEQUENCE = CONSTANT|4

class Primative(object):
    _layer = None
    _is_macro = False
    def __init__(self):
        self._staged = False
        self._committed = False

    def _stage(self, fsm_state):
        if self._staged:
            raise Exception("Primative already staged")
        self._staged = True
        return True

    def _commit(self, trans):
        if not self._staged:
            raise Exception("Primative must be staged before commit.")
        if self._committed:
            raise Exception("Primative already committed.")
        self._committed = True
        return False

    def __repr__(self):
        n = getattr(self, '_function_name', None) or \
            getattr(type(self), 'name', None) or \
            type(self).__name__
        return "<%s>"%n
    #    attrs = [attr+":"+str(getattr(self, attr)) for attr in dir(self) if attr[0] != '_']
    #    return "<P%d: %s (%s)>"%(self._layer, n, ", ".join(attrs))
    @property
    def _device_index(self):
        if hasattr(self, 'target_device'):
            return self.target_device.chain_index
        return None

    def snapshot(self):
        return {
            'valid':True,
            #'rowspan': not isinstance(self, DeviceTarget),
            'dev':self.target_device.chain_index \
                if hasattr(self, 'target_device') else "CHAIN",
            'name':getattr(self, '_function_name', None) or \
                getattr(type(self), 'name', None) or \
                type(self).__name__,
            'synthetic': self._synthetic if hasattr(self, '_synthetic')
                else False,
            'layer': type(self)._layer,
            'grouping': self._group_type,
            'data':{
                attr.replace("insname","INS"):
                getattr(self, attr)
                for attr in vars(self)
                if attr[0] != '_' and
                attr not in ["name", "target_device",
                             "required_effect"] and
                getattr(self, attr) is not None and
                not isinstance(getattr(self, attr), types.FunctionType)
            },
        }

class Executable(object):
    def execute(self):
        print("Executing", self.__class__.__name__)

class DeviceTarget(object):
    pass

class Level1Primative(Primative):
    _layer = 1
    _effect = [0, 0, 0]
    def __repr__(self):
        tms = self.tms
        tdi = self.tdi
        tdo = self.tdo
        if isinstance(self.tdi, bitarray):
            if len(self.tdi)>30:
                tdi = "%s...(%s bits)"%(tdi[0:30], len(tdi))
        if isinstance(self.tms, bitarray):
            if len(self.tms)>30:
                tms = "%s...(%s bits)"%(tms[0:30], len(tms))
        return "<%s(TMS:%s; TDI:%s; TDO:%s)>"%(self.__class__.__name__, tms, tdi, tdo)
class Level2Primative(Primative):
    _layer = 2
class Level3Primative(Primative):
    _layer = 3
    _is_macro = True




##########################################################################################
#LV3 Primatives

class DefaultRunInstructionPrimative(Level3Primative, DeviceTarget):
    name = "INS_PRIM"

    def __init__(self, device, insname, read=True, execute=True,
                 loop=0, arg=None, delay=0, synthetic=False):
        super(DefaultRunInstructionPrimative, self).__init__()
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
        #parts = ['ir', 'dr?', 'exe?', 'delay?', 'read?']
        f_seq = [
            [DefaultLoadDevIRPrimative(d,
                    bitarray(d._desc.
                             _instructions[frame[i].insname]))
             for i, d in enumerate(devs)]
        ]
        if frame._valid_prim.arg:
            f_seq.append([])
            for i, d in enumerate(devs):
                f_seq[-1].append(
                    DefaultLoadDevDRPrimative(d, frame[i].arg)
                )

        if frame._valid_prim.execute:
            f_seq.append([DefaultChangeTAPStatePrimative('TLR')])

        if any((p.delay for p in frame)):
            f_seq.append([DefaultSleepPrimative(max((p.delay for p in frame)))])

        if any((p.read for p in frame)):
            f_seq.append([])
            for i, d in enumerate(devs):
                f_seq[-1].append(
                    DefaultLoadDevDRPrimative(d, frame[i].read)
                )

        return f_seq

    def __repr__(self):
        n = getattr(self, '_function_name', None) or \
            getattr(type(self), 'name', None) or \
            type(self).__name__
        return "<%s(D:%s;exe:%s)>"%(n, self.target_device.chain_index, self.execute)

    def mergable(self, *target):
        return all((self._group_type == t._group_type and
                    isinstance(t, type(self)) for t in target))

    @property
    def _group_type(self):
        return (1 if self.execute else 0) +\
            (2 if self.arg is not None else 0)

    def get_placeholder_for_dev(self, dev):
        tmp = DefaultRunInstructionPrimative(
            dev, read=False,
            insname="BYPASS",
            execute=self.execute,
            arg=None if self.arg == None else bitarray(),
            synthetic=True)
        assert self._group_type == tmp._group_type
        return tmp

##########################################################################################
#LV2 Primatives

class DefaultChangeTAPStatePrimative(Level2Primative):
    _function_name = 'transition_tap'
    def __init__(self, state):
        super(DefaultChangeTAPStatePrimative, self).__init__()
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

class DefaultLoadDevDRPrimative(Level2Primative, DeviceTarget):
    _function_name = 'load_dev_dr'
    _is_macro = True
    def __init__(self, dev, data, read=False):
        super(DefaultLoadDevDRPrimative, self).__init__()
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


class DefaultLoadDevIRPrimative(Level2Primative, DeviceTarget):
    _function_name = 'load_dev_ir'
    _is_macro = True
    def __init__(self, dev, data, read=False):
        super(DefaultLoadDevIRPrimative, self).__init__()
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









class DefaultLoadReadDevRegisterPrimative(Level2Primative, DeviceTarget):
    _function_name = '_load_dev_register'
    def __init__(self, device, data, read=False, TMSLast=True, bitcount=None, synthetic=False):
        super(DefaultLoadReadDevRegisterPrimative, self).__init__()
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
        tmp = DefaultLoadReadDevRegisterPrimative(
            dev, data=bitarray(),
            read=False,
            bitcount=self.bitcount,
            TMSLast = self.TMSLast, #This needs to be reviewed
            synthetic=True)
        assert self._group_type == tmp._group_type
        return tmp














class DefaultChangeTAPStatePrimative2(Level2Primative):
    _function_name = 'transition_tap'
    def __init__(self, state):
        super(DefaultChangeTAPStatePrimative, self).__init__()
        self.targetstate = state
        self._startstate = None

    def _stage(self, fsm_state):
        super(DefaultChangeTAPStatePrimative, self)._stage(fsm_state)
        self._startstate = fsm_state
        return self.targetstate != fsm_state

    def _commit(self, command_queue):
        super(DefaultChangeTAPStatePrimative, self)._commit(command_queue)
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


class DefaultLoadReadRegisterPrimative(Level2Primative):
    _function_name = '_load_register'
    def __init__(self, data, read=False, TMSLast=True, bitcount=None):
        super(DefaultLoadReadRegisterPrimative, self).__init__()
        self.data = data
        self.read = read
        self.TMSLast = TMSLast
        self.bitcount=bitcount

    @property
    def _group_type(self):
        return 0

    def _stage(self, fsm_state):
        super(DefaultLoadReadRegisterPrimative, self)._stage(fsm_state)
        if fsm_state not in ["SHIFTIR", "SHIFTDR"]:
            return False

        if not ((self.bitcount if self.bitcount else len(self.data))>0):
            return False
        return True

    def _commit(self, command_queue):
        super(DefaultLoadReadRegisterPrimative, self)._commit(command_queue)
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


class DefaultReadDRPrimative(Level2Primative):
    _function_name = 'read_dr'
    _is_macro = True
    def __init__(self, bitcount):
        super(DefaultReadDRPrimative, self).__init__()
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

class DefaultLoadDRPrimative(Level2Primative):
    _function_name = 'load_dr'
    _is_macro = True
    def __init__(self, data, read):
        super(DefaultLoadDRPrimative, self).__init__()
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

class DefaultLoadIRPrimative(Level2Primative):
    _function_name = 'load_ir'
    _is_macro = True
    def __init__(self, data, read):
        super(DefaultLoadIRPrimative, self).__init__()
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

class DefaultSleepPrimative(Level2Primative, Executable):
    _function_name = 'sleep'
    _driver_function_name = 'sleep'
    def __init__(self, delay):
        super(DefaultSleepPrimative, self).__init__()
        self.delay = delay

    def _stage(self, fsm_state):
        super(DefaultSleepPrimative, self)._stage(fsm_state)
        return self.delay>0

    def _get_args(self):
        return [self.delay], {}

    def __repr__(self):
        return "<SLEEP(%s seconds)>"%(self.delay)

    @property
    def _group_type(self):
        return 0
