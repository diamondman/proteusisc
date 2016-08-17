from bitarray import bitarray
import types

from proteusisc.promise import TDOPromise

NOCARE = 0
ZERO = 1
ONE = 2
CONSTANT = ZERO|ONE
ARBITRARY = CONSTANT|4

class Primitive(object):
    _layer = None
    def __init__(self, _synthetic=False, *args, _chain, **kwargs):
        if args or kwargs:
            print(args)
            print(kwargs)
            print()
        assert not args and not kwargs
        super(Primitive, self).__init__()
        self._synthetic = _synthetic
        self._chain = _chain

    def __repr__(self):
        n = getattr(self, '_function_name', None) or \
            getattr(type(self), 'name', None) or \
            type(self).__name__
        parts = []
        if isinstance(self, DeviceTarget):
            parts.append("D:%s"%self.dev.chain_index)
        for v in vars(self):
            if v not in {"dev", "_promise", "_synthetic"}:
                value = getattr(self, v)
                if isinstance(value, bitarray):
                    value = value.to01()
                    if len(value) > 30:
                        value = str(value)[:30]+"...(%s)"%len(value)
                parts.append("%s:%s"%\
                             (v, value))

        return "<%s(%s)>" % (n, "; ".join(parts))

    def snapshot(self):
        return {
            'valid':True,
            'promise': self.get_promise() if isinstance(self, DataRW)
                       else None,
            'dev':self.dev.chain_index \
                if isinstance(self, DeviceTarget) else "CHAIN",
            'name':(getattr(self, '_function_name', None) or \
                getattr(type(self), 'name', None) or \
                type(self).__name__).upper(),
            'synthetic': self._synthetic,
            'layer': type(self)._layer,
            'grouping': self._group_type,
            'data':{
                attr.replace("insname","INS"):
                getattr(self, attr) if not
                    isinstance(getattr(self, attr), bitarray)
                    else getattr(self, attr).to01()
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


class Executable(Primitive):
    def execute(self):
        raise NotImplemented()

class ExpandRequiresTAP(Primitive):
    pass

class DataRW(Primitive):
    def __init__(self, data=None, read=False, _promise=None,
                 *args, **kwargs):
        super(DataRW, self).__init__(*args, **kwargs)
        self.data = data
        self.read = read
        self._promise = _promise

    def get_promise(self):
        if self._promise is None and self.read:
            self._promise = TDOPromise(self._chain)
        return self._promise

class DeviceTarget(DataRW):
    def __init__(self, *args, dev, **kwargs):
        super(DeviceTarget, self).__init__(*args, **kwargs)
        self.dev  = dev

    def get_placeholder_for_dev(self, dev):
        raise NotImplementedError()

    @property
    def _device_index(self):
        return self.dev.chain_index

class Level1Primitive(Primitive):
    _layer = 1
    _effect = [0, 0, 0]
    def __init__(self, count, tms, tdi, tdo, *args, **kwargs):
        super(Level1Primitive, self).__init__(*args, **kwargs)
        self.count, self.tms, self.tdi, self.tdo = count, tms, tdi, tdo

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

    def merge(self, target):
        if not isinstance(target, Level1Primitive):
            return None
        print(('  \033[95m%s %s %s\033[94m'%tuple(self._effect))\
              .replace('0', '-'), self,'\033[0m')
        print(('  \033[95m%s %s %s\033[94m'%tuple(target._effect))\
              .replace('0', '-'), target,'\033[0m')
        #7 7 2 <LIESTDIHighPrimitive(TMS:bitarray('1111'); TDI:0; TDO:0)>
        #7 7 3 <DigilentWriteTMSPrimitive(TMS:; TDI:0; TDO:0)>
        #7 7 2 CONBINED

        #2 = ONE
        #3 = CONSTANT

        #TMS TDI TDO
        reqef = list(self._effect)
        attrnames = ('tms','tdi','tdo')
        for i in range(3):
            curr = reqef[i] #2
            other = target._effect[i] #3
            if not curr:
                reqef[i] = other
            elif not other:
                pass
            elif curr is CONSTANT and other is CONSTANT:
                if getattr(self, attrnames[i]) != \
                   getattr(target, attrnames[i]):
                    reqef[i] = ARBITRARY
            elif (curr is CONSTANT and other in {ZERO, ONE}) or\
                 (other is CONSTANT and curr in {ZERO, ONE}):
                if getattr(self, attrnames[i]) == \
                   getattr(target, attrnames[i]):
                    reqef[i] = CONSTANT
                else:
                    reqef[i] = ARBITRARY
            elif curr is ARBITRARY or other is ARBITRARY:
                reqef[i] = ARBITRARY
            elif curr is not CONSTANT and other is not CONSTANT and\
                 (curr|other is CONSTANT):
                reqef[i] = ARBITRARY

        print(('  \033[95m%s %s %s\033[94m'%tuple(reqef))\
              .replace('0', '-'), "CONBINED",'\033[0m')


        best_prim = self._chain.get_best_lv1_prim(reqef)

        return best_prim(self.count+target.count,0,0,0,
                         _chain=self._chain)

    def expand(self, chain, sm):
        return None

class Level2Primitive(Primitive):
    _layer = 2
    def merge(self, target):
        if type(self) == type(target):
            kwargs = {'_chain': self._chain}
            if isinstance(self, DeviceTarget) and self.dev is target.dev:
                kwargs['dev'] = self.dev
            if isinstance(self, DataRW) and  self.read and \
               not self.data and not target.read:
                kwargs['read'] = True
                kwargs['data'] = target.data
                kwargs['_promise'] = self._promise
            return type(self)(**kwargs)
        return None

class Level3Primitive(Primitive):
    _layer = 3
