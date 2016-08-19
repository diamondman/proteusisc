from bitarray import bitarray
import types
import operator
import collections

from proteusisc.promise import TDOPromise

class Requirement(object):
    """Represents the ability of a ISC Controller to transmit data on a
    signal (wire). A LV1 primitives have different levels of
    expressiveness per signal.  For each signal, a primitive be able
    tos end one of the following 4 values during the primitive's
    execution:

        Only 0 (Primitive always sets signal to 0)
        Only 1 (Primitive always sets signal to 1)
        Either 0 OR 1 (Constant for the full primitive execution)
        Any arbitrary sequence of 0 and 1.

    This class is wrapping a 4 bit number:
    ABCD
    1XXX = ARBITRARY (A)
    000X = NOCARE (-)
    0010 = ZERO (0)
    0011 = ONE (1)
    01X0 = (CONSTANT) ZERO. use ZERO (C0)
    01X1 = (CONSTANT) ONE. use ONE (C1)

    A Requirement instance can behave in two ways:
        Describe the capability of a primitive with respect to a signal:
            Constant specifies that the primitive can send either 0 or 1
            to the respective signal.
        Describe matching requirements for expanding primitives
            Constant is treated the same as single since it is just the
            requirement of an existing primitive.

    """
    def __init__(self, arbitrary, constant, single, value):
        self.arbitrary = arbitrary
        self.constant = constant
        self.single = single
        self.value = value

    def copy(self):
        return Requirement(self.arbitrary, self.constant, self.single,
                           self.value)

    @property
    def A(self):
        return self.arbitrary
    @property
    def B(self):
        return self.constant
    @property
    def C(self):
        return self.single
    @property
    def D(self):
        return self.value
    @property
    def isnocare(self):
        return not self.arbitrary and not self.constant \
            and not self.single

    def satisfies(self, other):
        """
             other
              A C 0 1
           |Y N N N N
        s A|Y Y Y Y Y
        e C|Y - Y Y Y
        l 0|Y * * Y N
        f 1|Y * * N Y

        ' ' = No Care
        A = arbitrary
        C = Constant
        0 = ZERO
        1 = ONE

        Y = YES
        N = NO
        - = Could satisfy with multiple instances
        * = Not yet determined behavior. Used for bitbanging controllers.

        """
        if other.isnocare:
            return True
        if self.isnocare:
            return False
        if self.arbitrary:
            return True
        if self.constant and not other.arbitrary:
            return True
        if self.value is other.value and not other.arbitrary:
            return True
        return False

    @property
    def score(self):
        return sum([v<<i for i, v in
                    enumerate(reversed(
                        (self.A, self.B, self.C))
                    )])

    def __repr__(self):
        if self.arbitrary:
            l = 'A'
        elif self.constant:
            l = "C"
        elif self.single:
            l = "F" if self.value else "T"
        else:
            l = "-"
        return l+"("+bin(sum([v<<i for i, v in
                        enumerate(reversed(
                            (self.A, self.B, self.C, self.D))
                        )]))[2:].zfill(4) +")"

    def __add__(self, other):
        """
        Combines two Requirements.

        Assumes both Requirements are being used as feature requests.
        Adding two Requirements being used as feature lists for a
        primitive has no meaning.

        The following code is a reduced K-map of the full interaction
        of two Requirement objects. For details, see
        requirements_description.txt in the documentation.
        """
        if not isinstance(other, Requirement):
            return NotImplemented
        a1, a2, a3, a4, b1, b2, b3, b4 = self.A, self.B, self.C, self.D, other.A, other.B, other.C, other.D
        A = (a1 or a2 or a3 or b1)and(a1 or a4 or b1 or b4)and(a1 or b1 or b2 or b3)and(a1 or not a4 or b1 or not b4)
        B = False
        C = b3 or b2 or a3 or a2
        D = (a2 or a3 or b4)and(a4 or b2 or b3)and(a4 or b4)
        res = Requirement(A, B, C, D)
        #print(self, a1, a2, a3, a4)
        #print(other, b1, b2, b3, b4)
        #print(res, A, B, C, D, "\n")
        return res

NOCARE =       Requirement(False, False, False, False)
ZERO =         Requirement(False, False, True,  False)
ONE =          Requirement(False, False, True,  True)
CONSTANT    =  Requirement(False, True,  False, False)
CONSTANTZERO = Requirement(False, True,  False, False)
CONSTANTONE =  Requirement(False, True,  False, True)
ARBITRARY =    Requirement(True,  False, False, False)

class ConstantBitarray(collections.Sequence):
    def __init__(self, val, length):
        self._val = bool(val)
        self._length = length

    def __len__(self):
        return self._length
    def __getitem__(self, index):
        if index < self._length and index >= 0:
            return self._val
        raise IndexError("ConstantBitarray index out of range")
    def __repr__(self):
        return "<Const: %s (%s)>"%(self._val, self._length)
    def __add__(self, other):
        if isinstance(other, ConstantBitarray):
            if self._val == other._val:
                return ConstantBitarray(self._val,
                                        self._length+other._length)
            else:
                return bitarray((*(self._val,)*self._length,
                                 *(other._val,)*other._length))
        if isinstance(other, bool):
            if self._val == other:
                return ConstantBitarray(self._val, self._length+1)
            else:
                return bitarray((*(self._val,)*self._length, other))
        if isinstance(other, bitarray):
            return bitarray(self)+other
        return NotImplemented

class NoCareBitarray(collections.Sequence):
    def __init__(self, length):
        self._length = length

    def __len__(self):
        return self._length
    def __getitem__(self, index):
        if index < self._length and index >= 0:
            return False
        raise IndexError("NoCareBitarray index out of range")
    def __repr__(self):
        return "<NC: (%s)>"%(self._length)
    def __add__(self, other):
        if isinstance(other, NoCareBitarray):
            return NoCareBitarray(self._length+other._length)
        if isinstance(other, ConstantBitarray):
            return ConstantBitarray(other._val,
                                    self._length+other._length)
        if isinstance(other, bool):
            return ConstantBitarray(other, self._length+1)
        if isinstance(other, bitarray):
            return bitarray(self)+other
        return NotImplemented
    def __radd__(self, other):
        if isinstance(other, ConstantBitarray):
            return ConstantBitarray(other._val,
                                    self._length+other._length)
        if isinstance(other, bool):
            return ConstantBitarray(other, self._length+1)
        return NotImplemented

class Primitive(object):
    _layer = None
    def __init__(self, *args, _chain, _synthetic=False, **kwargs):
        if args or kwargs:
            print(type(self))
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
                getattr(self, attr) #if not
                #    isinstance(getattr(self, attr), bitarray)
                #    else getattr(self, attr).to01()
                for attr in vars(self)
                if attr[0] != '_' and
                attr not in ["name", "dev", "required_effect"] and
                getattr(self, attr) is not None and
                not isinstance(getattr(self, attr), types.FunctionType)
            },
        }

    def signature(self):
        return self, self._group_type

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

class Level3Primitive(Primitive):
    _layer = 3

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

class Level1Primitive(Primitive):
    _layer = 1
    _TMS = NOCARE
    _TDI = NOCARE
    _TDO = NOCARE
    @classmethod
    def get_effect(cls):
        return (cls._TMS, cls._TDI, cls._TDO)
    def __init__(self, count=None, tms=None, tdi=None, tdo=None,
                 *args, reqef, **kwargs):
        super(Level1Primitive, self).__init__(*args, **kwargs)
        _tms, _tdi, _tdo = tms, tdi, tdo

        self.reqef = reqef

        if isinstance(_tms, collections.Iterable):
            count = count or len(_tms)
        if isinstance(_tdi, collections.Iterable):
            count = count or len(_tdi)
        if isinstance(_tdo, collections.Iterable):
            count = count or len(_tdo)
        if count is None:
            count = 1
            #raise ValueError("Length not specified or inferable")

        if _tms is None:
            _tms = NoCareBitarray(count)
        elif not isinstance(_tms, collections.Iterable):
            _tms = ConstantBitarray(_tms, count)
        if _tdi is None:
            _tdi = NoCareBitarray(count)
        elif not isinstance(_tdi, collections.Iterable):
            _tdi = ConstantBitarray(_tdi, count)
        if _tdo is None:
            _tdo = NoCareBitarray(count)
        elif not isinstance(_tdo, collections.Iterable):
            _tdo = ConstantBitarray(_tdo, count)

        if len(_tms) != count:
            raise ValueError("TMS is the wrong length")
        if len(_tdi) != count:
            raise ValueError("TDI is the wrong length")
        if len(_tdo) != count:
            raise ValueError("TDO is the wrong length")

        self.count, self.tms, self.tdi, self.tdo = count, _tms, _tdi, _tdo
        print(type(self).get_effect())

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
        print(('  \033[95m%s %s %s REQEF\033[94m'%tuple(self.reqef)),
              self,'\033[0m')
        print(('  \033[95m%s %s %s REQEF\033[94m'%tuple(target.reqef)),
              target,'\033[0m')

        #TMS TDI TDO
        reqef = tuple(map(operator.add, self.reqef, target.reqef))

        print(('  \033[95m%s %s %s\033[94m'%tuple(reqef)),
              "CONBINED",'\033[0m')

        best_prim = self._chain.get_fitted_lv1_prim(reqef)

        return best_prim(count=self.count+target.count,
                         tms=self.tms+target.tms,
                         tdi=self.tdi+target.tdi,
                         tdo=self.tdo+target.tdo)

    def expand(self, chain, sm):
        return None


class TMSArbitrary(Level1Primitive):
    _TMS = ARBITRARY
    #def __init__(self, *args, tms=None, **kwargs):
    #    super(TMSArbitrary, self).__init__(_tms=tms, *args, **kwargs)
class TMSConst(Level1Primitive):
    _TMS = CONSTANT
    #def __init__(self, *args, tms=None, **kwargs):
    #    super(TMSConst, self).__init__(_tms=tms, *args, **kwargs)
class TMSZero(Level1Primitive):
    _TMS = ZERO
    #def __init__(self, *args, **kwargs):
    #    super(TMSZero, self).__init__(_tms=False, *args, **kwargs)
class TMSOne(Level1Primitive):
    _TMS = ONE
    #def __init__(self, *args, **kwargs):
    #    super(TMSOne, self).__init__(_tms=True, *args, **kwargs)

class TDIArbitrary(Level1Primitive):
    _TDI = ARBITRARY
    #def __init__(self, *args, tdi=None, **kwargs):
    #    super(TDIArbitrary, self).__init__(_tdi=tdi, *args, **kwargs)
class TDIConst(Level1Primitive):
    _TDI = CONSTANT
    #def __init__(self, *args, tdi=None, **kwargs):
    #    super(TDIConst, self).__init__(_tdi=tdi, *args, **kwargs)
class TDIZero(Level1Primitive):
    _TDI = ZERO
    #def __init__(self, *args, **kwargs):
    #    super(TDIZero, self).__init__(_tdi=False, *args, **kwargs)
class TDIOne(Level1Primitive):
    _TDI = ONE
    #def __init__(self, *args, **kwargs):
    #    super(TDIOne, self).__init__(_tdi=True, *args, **kwargs)

class TDOArbitrary(Level1Primitive):
    _TDO = ARBITRARY
    #def __init__(self, *args, tdo=None, **kwargs):
    #    super(TDOArbitrary, self).__init__(_tdo=tdo, *args, **kwargs)
class TDOConst(Level1Primitive):
    _TDO = CONSTANT
    #def __init__(self, *args, tdo=None, **kwargs):
    #    super(TDOConst, self).__init__(_tdo=tdo, *args, **kwargs)
class TDOZero(Level1Primitive):
    _TDO = ZERO
    #def __init__(self, *args, **kwargs):
    #    super(TDOZero, self).__init__(_tdo=False, *args, **kwargs)
class TDOOne(Level1Primitive):
    _TDO = ONE
    #def __init__(self, *args, **kwargs):
    #    super(TDOOne, self).__init__(_tdo=True, *args, **kwargs)
