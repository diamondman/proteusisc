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

    def signature(self):
        return (type(self), self._group_type)

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
