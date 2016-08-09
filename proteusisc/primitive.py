from bitarray import bitarray
import types

from proteusisc.promise import TDOPromise

DOESNOTMATTER = 0
ZERO = 1
ONE = 2
CONSTANT = ZERO|ONE
SEQUENCE = CONSTANT|4

class Primitive(object):
    _layer = None
    def __init__(self, _synthetic=False, *args, **kwargs):
        if args or kwargs:
            print(args)
            print(kwargs)
            print()
        assert not args and not kwargs
        super(Primitive, self).__init__()
        self._synthetic = _synthetic
        self._chain = None

    def __repr__(self):
        n = getattr(self, '_function_name', None) or \
            getattr(type(self), 'name', None) or \
            type(self).__name__
        parts = []
        if isinstance(self, DeviceTarget):
            parts.append("D:%s"%self.dev.chain_index)
        for v in vars(self):
            if v not in {"dev"}:
                parts.append("%s:%s"%\
                             (v, getattr(self, v)))

        return "<%s(%s)>" % (n, "; ".join(parts))

    def snapshot(self):
        return {
            'valid':True,
            'promise': self.get_promise() if isinstance(self, DataRW)
                       else None,
            'dev':self.dev.chain_index \
                if isinstance(self, DeviceTarget) else "CHAIN",
            'name':getattr(self, '_function_name', None) or \
                getattr(type(self), 'name', None) or \
                type(self).__name__,
            'synthetic': self._synthetic,
            'layer': type(self)._layer,
            'grouping': self._group_type,
            'data':{
                attr.replace("insname","INS"):
                getattr(self, attr)
                for attr in vars(self)
                if attr[0] != '_' and
                attr not in ["name", "dev", "required_effect"] and
                getattr(self, attr) is not None and
                not isinstance(getattr(self, attr), types.FunctionType)
            },
        }

    def signature(self):
        return (type(self), self._group_type)

    @property
    def _group_type(self):
        return 0


class Executable(object):
    def execute(self):
        raise NotImplemented()

class DeviceTarget(Primitive):
    def __init__(self, *args, dev, **kwargs):
        super(DeviceTarget, self).__init__(*args, **kwargs)
        self.dev  = dev

    def get_placeholder_for_dev(self, dev):
        print(self, dev)
        raise NotImplementedError()

    @property
    def _device_index(self):
        return self.dev.chain_index

class DataRW(Primitive):
    def __init__(self, data=None, read=False, _promise=None, *args, **kwargs):
        super(DataRW, self).__init__(*args, **kwargs)
        self.data = data
        self.read = read
        self._promise = _promise

    def get_promise(self):
        if self._promise is None and self.read:
            self._promise = TDOPromise(self._chain)
        return self._promise

class Level1Primitive(Primitive):
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
        return "<%s(TMS:%s; TDI:%s; TDO:%s)>"%\
            (self.__class__.__name__, tms, tdi, tdo)

class Level2Primitive(Primitive):
    _layer = 2
    def mergable(self, target):
        return False

class Level3Primitive(Primitive):
    _layer = 3
