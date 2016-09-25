from bitarray import bitarray
import types
import operator
import collections

from .promise import TDOPromise, TDOPromiseCollection
from .bittypes import ConstantBitarray, NoCareBitarray
from .contracts import NOCARE

class Primitive(object):
    _layer = None
    _id = 0
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
        self.pid = Primitive._id
        Primitive._id += 1

    def __repr__(self):
        n = getattr(self, '_function_name', None) or \
            getattr(type(self), 'name', None) or \
            type(self).__name__
        parts = []
        if isinstance(self, DeviceTarget):
            # pylint: disable=no-member
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
        # pylint: disable=no-member
        return {
            'valid':True,
            'promise': self.get_promise(),
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
                getattr(self, attr)
                for attr in vars(self)
                if attr[0] != '_' and
                attr not in ["name", "dev", "required_effect"] and
                #getattr(self, attr) is not None and
                not isinstance(getattr(self, attr), types.FunctionType)
            },
        }

    def signature(self):
        return type(self), self._group_type

    @property
    def _group_type(self):
        return 0

    def get_promise(self):
        return None

    @property
    def debug(self):
        if self._chain:
            return self._chain._debug
        return False


class Executable(Primitive):
    def execute(self):
        raise NotImplementedError()

class ExpandRequiresTAP(Primitive):
    pass

class DataRW(Primitive):
    def __init__(self, *args, data=None, bitcount=None, read=False,
                 _promise=None, **kwargs):
        super(DataRW, self).__init__(*args, **kwargs)
        self.data = data
        self.bitcount = bitcount
        self.read = read
        #If promise must be used during init, please read the comment
        #in Level1Primitive.merge where the new promise is calculated.
        self._promise = _promise

    def get_promise(self):
        if self._promise is None and self.read:
            self._promise = TDOPromise(self._chain, 0, self.bitcount)
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
        return None

class Level1Primitive(Primitive):
    _layer = 1
    _TMS = NOCARE
    _TDI = NOCARE
    _TDO = NOCARE
    @classmethod
    def get_effect(cls):
        return (cls._TMS, cls._TDI, cls._TDO)
    def __init__(self, *args, count=None, tms=None, tdi=None, tdo=None,
                 _promise=None, reqef, **kwargs):
        super(Level1Primitive, self).__init__(*args, **kwargs)
        _tms, _tdi, _tdo = tms, tdi, tdo

        self.reqef = reqef
        self._promise = _promise

        if isinstance(_tms, collections.Iterable):
            count = count or len(_tms)
        if isinstance(_tdi, collections.Iterable):
            count = count or len(_tdi)
        if isinstance(_tdo, collections.Iterable):
            count = count or len(_tdo)
        if count is None:
            count = 1

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

        #if self._promise and not any(self.tdo):
        if self.debug:
            print(type(self).get_effect())

    _COST_PRIM = 20
    _COST_READ_MSG = 10
    _COST_READ_BIT_GROUP = 1
    _COST_PAYLOAD_BIT_GROUP = 1
    _BIT_READ_GROUP_SIZE = 1
    _BIT_PAYLOAD_GROUP_SIZE = 1

    @property
    def score(self):
        readenabled = self.tdo.any() or\
                      (self._TDO.single and self._TDO.value)
        readcount = self.tdo.count() if self._TDO.arbitrary else\
                    (self.count if (self._TDO.value or self.tdo.any())\
                     else 0)
        tdosendcount = len(self.tdo)*self._TDO.arbitrary
        tmssendcount = len(self.tms)*self._TMS.arbitrary
        tdisendcount = len(self.tdi)*self._TDI.arbitrary

        if self.debug:
            print("Reading",readenabled, "Readnum",readcount,
                  "tmsnum", tmssendcount, "tdinum",tdisendcount)

        SEND_COEFF = (self._COST_PAYLOAD_BIT_GROUP+
                       self._BIT_PAYLOAD_GROUP_SIZE-1)//\
                       self._BIT_PAYLOAD_GROUP_SIZE
        RECV_COEFF = (self._COST_READ_BIT_GROUP+
                      self._BIT_READ_GROUP_SIZE-1)//\
                      self._BIT_READ_GROUP_SIZE

        readenablecost = (readenabled*self._COST_READ_MSG)
        readbitcost = readcount*RECV_COEFF
        readbitreqcost = tdosendcount*SEND_COEFF
        writetmscost = tmssendcount*SEND_COEFF
        writetdicost =  tdisendcount*SEND_COEFF

        if self.debug:
            print("Base cost        ", self._COST_PRIM)
            print("Read Enable Cost ", readenablecost)
            print("Read Bit Req Cost", readbitreqcost)
            print("Read Bit Cost    ", readbitcost)
            print("Write tms Cost   ", writetmscost)
            print("Write tdi Cost   ", writetdicost)

        return self._COST_PRIM + readenablecost +\
            readbitreqcost + readbitcost + writetmscost + writetdicost

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
        if isinstance(self.tdo, bitarray):
            if len(self.tdo)>30:
                tdo = "%s...(%s bits)"%(tdo[0:30], len(tdo))
        return "<%s(TMS:%s; TDI:%s; TDO:%s)>"%\
            (self.__class__.__name__, tms, tdi, tdo)

    def merge(self, target):
        if not isinstance(target, Level1Primitive):
            return None
        if self.debug:
            print(('  \033[95m%s %s %s REQEF\033[94m'%tuple(self.reqef)),
                  self,'\033[0m')
            print(('  \033[95m%s %s %s REQEF\033[94m'%tuple(target.reqef)),
                  target,'\033[0m')

        newcount = target.count+self.count

        reqef = tuple(map(operator.add, self.reqef, target.reqef))

        newtms = target.tms+self.tms
        newtdi = target.tdi+self.tdi
        newtdo = target.tdo+self.tdo

        if self.debug:
            print(('  \033[95m%s %s %s\033[94m'%tuple(reqef)),
                  "CONBINED",'\033[0m')

        possible_prims = self._chain.get_compatible_lv1_prims(reqef)
        best_prim = None
        best_score = self.score + target.score
        for prim_cls in possible_prims:
            tmp_prim = prim_cls(count=newcount,
                                tms=newtms, tdi=newtdi,
                                tdo=newtdo, reqef=reqef,
                                _chain=self._chain)#, _promise=promise)

            if self.debug:
                print(tmp_prim.score, tmp_prim)
            if tmp_prim.score < best_score:
                best_prim = tmp_prim
                best_score = tmp_prim.score
        if self.debug:
            print("PICKED", best_prim, "\n")

        if best_prim:
            if not self._promise and not target._promise:
                promise = None
            elif self._promise and not target._promise:
                promise = self._promise.makesubatoffset(target.count)
            elif not self._promise and target._promise:
                promise = target._promise
            else:
                promise = TDOPromiseCollection(self._chain, newcount)
                promise.add(target._promise, 0)
                promise.add(self._promise, target.count)

            #This is a bit of a hack. It is difficult to undo
            #subpromises. If primitives later use the promise
            #during init, this must change
            best_prim._promise = promise
        return best_prim

    def expand(self, chain, sm):
        return None

    def get_promise(self):
        return self._promise
