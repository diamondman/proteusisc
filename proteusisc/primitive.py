from abc import ABCMeta, abstractmethod
import collections
from functools import partial
import operator
import types

from .bittypes import CompositeBitarray, ConstantBitarray, \
    NoCareBitarray, bitarray, PreferFalseBitarray
from .contracts import ARBITRARY, CONSTANTZERO, ZERO, NOCARE
from .promise import TDOPromise, TDOPromiseCollection

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
                if isinstance(value, bitarray):#TODO fix this for compba
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
                repr(val) if isinstance(val, CompositeBitarray) else val
                for attr, val in vars(self).items()
                if attr[0] != '_' and
                attr not in ["name", "dev", "required_effect"] and
                #getattr(self, attr) is not None and
                not isinstance(val, types.FunctionType)
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

    def can_join_frame(self, f):
        return True


class Executable(metaclass=ABCMeta):
    @abstractmethod
    def execute(self):
        raise NotImplementedError()

class ExpandRequiresTAP(Primitive):
    pass

class DataRW(Primitive):
    def __init__(self, *args, data=None, bitcount=None, read=False,
                 _promise=None, **kwargs):
        super(DataRW, self).__init__(*args, **kwargs)
        if isinstance(data, bitarray):
            self.data = CompositeBitarray(data)
        else:
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
        _tms, _tdi, _tdo =\
            CompositeBitarray(tms) if isinstance(tms, bitarray) else tms,\
            CompositeBitarray(tdi) if isinstance(tdi, bitarray) else tdi,\
            CompositeBitarray(tdo) if isinstance(tdo, bitarray) else tdo

        self.reqef = reqef
        self._promise = _promise

        if count is None:
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
            _tdo = PreferFalseBitarray(count)
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

    @classmethod
    def _calc_score(cls, count, reqef, tdo_count, *, debug=False):
        readenabled = (cls._TDO.single and cls._TDO.value) or\
                      tdo_count > 0

        readcount = tdo_count if cls._TDO.arbitrary else\
                    (count if (cls._TDO.value or (tdo_count > 0))\
                     else 0)
        tdosendcount = count*cls._TDO.arbitrary
        tmssendcount = count*cls._TMS.arbitrary
        tdisendcount = count*cls._TDI.arbitrary

        if debug:
            print("Reading",readenabled, "Readnum",readcount,
                  "tmsnum", tmssendcount, "tdinum",tdisendcount)

        SEND_COEFF = (cls._COST_PAYLOAD_BIT_GROUP+
                       cls._BIT_PAYLOAD_GROUP_SIZE-1)//\
                       cls._BIT_PAYLOAD_GROUP_SIZE
        RECV_COEFF = (cls._COST_READ_BIT_GROUP+
                      cls._BIT_READ_GROUP_SIZE-1)//\
                      cls._BIT_READ_GROUP_SIZE

        readenablecost = (readenabled*cls._COST_READ_MSG)
        readbitcost = readcount*RECV_COEFF
        readbitreqcost = tdosendcount*SEND_COEFF
        writetmscost = tmssendcount*SEND_COEFF
        writetdicost =  tdisendcount*SEND_COEFF

        if debug:
            print("Base cost        ", cls._COST_PRIM)
            print("Read Enable Cost ", readenablecost)
            print("Read Bit Req Cost", readbitreqcost)
            print("Read Bit Cost    ", readbitcost)
            print("Write tms Cost   ", writetmscost)
            print("Write tdi Cost   ", writetdicost)

        return cls._COST_PRIM + readenablecost +\
            readbitreqcost + readbitcost + writetmscost + writetdicost


    @property
    def score(self):
        return type(self)._calc_score(self.count,self.reqef,
                                      self.tdo.count(True),
                                      debug=self.debug)

    def __repr__(self):
        #Make work with CompositeBitarray
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

    @classmethod
    def can_prim_handle_bitcount(cls, reqef, bitcount):
        #Does not support arbitrary TDO with recv bits < send bits
        tdoef = reqef[2]
        if tdoef == ARBITRARY and cls._max_send_bits > cls._max_recv_bits:
            raise NotImplementedError("Does not yet support ARBITRARY "
                                      "TDO with mismatch mas recv and "
                                      "send.")
        return bitcount <= cls._max_send_bits and\
            (bitcount <= cls._max_recv_bits or\
             tdoef in (CONSTANTZERO, ZERO, NOCARE))

    def merge(self, target):
        if not isinstance(target, Level1Primitive):
            return None
        if self.debug:
            print(('  \033[95m%s %s %s REQEF\033[94m'%tuple(self.reqef)),
                  self,'\033[0m')
            print(('  \033[95m%s %s %s REQEF\033[94m'%
                   tuple(target.reqef)), target,'\033[0m')

        newcount = target.count+self.count
        reqef = tuple(map(operator.add, self.reqef, target.reqef))

        if self.debug:
            print(('  \033[95m%s %s %s\033[94m'%tuple(reqef)),
                  "CONBINED",'\033[0m')

        possible_prims = self._chain.get_compatible_lv1_prims(
            reqef)#, newcount)
        #if not possible_prims:
        #    return
        best_prim_cls = None
        best_score = self.score + target.score
        tdo_count = target.tdo.count(True)+self.tdo.count(True)
        for prim_cls in possible_prims:
            if not prim_cls.can_prim_handle_bitcount(reqef, newcount):
                continue
            prim_score = prim_cls._calc_score(newcount, reqef, tdo_count,
                                              debug=self.debug)
            if self.debug:
                print(prim_score, prim_cls)
            if prim_score < best_score:
                best_prim_cls = prim_cls
                best_score = prim_score

        if self.debug:
            print("PICKED", best_prim_cls, "\n")

        if best_prim_cls:
            newtms = target.tms+self.tms
            newtdi = target.tdi+self.tdi
            newtdo = target.tdo+self.tdo

            if not self._promise and not target._promise:
                promise = None
            elif self._promise and not target._promise:
                promise = self._promise.makesubatoffset(target.count,
                                                        _offsetideal=0)
            elif not self._promise and target._promise:
                promise = target._promise
            else:
                promise = TDOPromiseCollection(self._chain)
                promise.add(target._promise, 0)
                promise.add(self._promise, target.count)

            return best_prim_cls(count=newcount,
                                 tms=newtms, tdi=newtdi,
                                 tdo=newtdo, reqef=reqef,
                                 _chain=self._chain, _promise=promise)

    def expand(self, chain, sm):
        return None

    def get_promise(self):
        return self._promise

    def execute(self, controller):
        if self._chain and self._chain._print_statistics:
            print("\nRunning %s bits; Type: %s" % \
                  (self.count, type(self)._driver_function_name))\
                  #pragma: no cover
        self.prepare_args()
        func = getattr(controller, self._driver_function_name, None)
        if not func:
            raise Exception(
                "Registered function %s not found on class %s"%\
                (self._driver_function_name, controller.__class__))

        from time import time
        t = time()
        args, kwargs = self.get_args()
        if self._chain and self._chain._print_statistics:
            print("DRIVER FUNCTION ARGUMENT PREPARE TIME", time()-t)\
                #pragma: no cover

        res = func(*args, **kwargs)
        if res and self._promise:
            if self._chain and self._chain._debug:#pragma: no cover
                print("RAW DATA GOING TO PROMISE", res, len(res))
            self._promise._fulfill(
                res, ignore_nonpromised_bits=self._TDO.isarbitrary)

    def prepare_args(self):
        if len(self.tms) != self.count:
            raise Exception("TMS is wrong length")
        if len(self.tdi) != self.count:
            raise Exception("TDI is wrong length")
        if len(self.tdo) != self.count:
            raise Exception("TDO is wrong length")

        if not isinstance(self.tms, CompositeBitarray):
            self.tms = CompositeBitarray(self.tms)
        self.tms = self.tms.prepare(
            primef=self._TMS, reqef=self.reqef[0])

        if not isinstance(self.tdi, CompositeBitarray):
            self.tdi = CompositeBitarray(self.tdi)
        self.tdi = self.tdi.prepare(
            primef=self._TDI, reqef=self.reqef[1])

        if not isinstance(self.tdo, CompositeBitarray):
            self.tdo = CompositeBitarray(self.tdo)
        self.tdo = self.tdo.prepare(
            primef=self._TDO, reqef=self.reqef[2])

        if not self._TMS.isarbitrary:
            if isinstance(self.tms, (NoCareBitarray,
                                     PreferFalseBitarray)):
                self.tms = False
            elif isinstance(self.tms, ConstantBitarray):
                self.tms = self.tms._val

        if not self._TDI.isarbitrary:
            if isinstance(self.tdi, (NoCareBitarray,
                                     PreferFalseBitarray)):
                self.tdi = False
            elif isinstance(self.tdi, ConstantBitarray):
                self.tdi = self.tdi._val

        if not self._TDO.isarbitrary:
            if isinstance(self.tdo, (NoCareBitarray,
                                     PreferFalseBitarray)):
                self.tdo = False
            elif isinstance(self.tdo, ConstantBitarray):
                self.tdo = self.tdo._val

    def get_args(self):
        if not hasattr(self, '_args'):
            raise Exception('Primitive class does not provide _args')
        if not hasattr(self, '_kwargs'):
            raise Exception('Primitive class does not provide _kwargs')
        args = [getattr(self, attr) for attr in self._args]
        kwargs = {k:getattr(self, v) for k,v in self._kwargs.items()}
        return args, kwargs


class PrimitiveLv1Dispatcher(object):
    def __init__(self, chain, primcls, reqef):
        self._chain = chain
        self._primcls = primcls
        self._reqef = reqef

    def __call__(self, *args, count=None, tms=None, tdi=None, tdo=None,
                 **kwargs):
        maxbits = self._primcls._max_send_bits
        if self._primcls._max_recv_bits < maxbits and\
             self._reqef[2] not in (CONSTANTZERO, ZERO, NOCARE):
            maxbits = self._primcls._max_recv_bits

        primgen = partial(self._primcls, _chain=self._chain,
                       reqef=self._reqef)


        if isinstance(tms, collections.Iterable):
            count = count or len(tms)
        if isinstance(tdi, collections.Iterable):
            count = count or len(tdi)
        if isinstance(tdo, collections.Iterable):
            count = count or len(tdo)

        #No need to split up data
        if count <= maxbits:
            return [primgen(*args, count=count,
                            tms=tms, tdi=tdi, tdo=tdo, **kwargs)]

        #Have to split up data
        istms, istdi, istdo = True, True, True
        if not isinstance(tms, collections.Iterable):
            kwargs['tms'] = tms
            istms = False
        if not isinstance(tdi, collections.Iterable):
            kwargs['tdi'] = tdi
            istdi = False
        if not isinstance(tdo, collections.Iterable):
            kwargs['tdo'] = tdo
            istdo = False

        tms, tdi, tdo =\
            CompositeBitarray(tms) if isinstance(tms, bitarray) else tms,\
            CompositeBitarray(tdi) if isinstance(tdi, bitarray) else tdi,\
            CompositeBitarray(tdo) if isinstance(tdo, bitarray) else tdo

        kwargs['count'] = maxbits
        _promise = kwargs.pop("_promise", None)
        orig_promise = _promise

        #print("ORIGINAL PROMISE", _promise)
        primitives = []
        for i in range(count//maxbits):
            if istms:
                tms, kwargs['tms'] = tms.split(len(tms)-maxbits)
            if istdi:
                tdi, kwargs['tdi'] = tdi.split(len(tdi)-maxbits)
            if istdo:
                tdo, kwargs['tdo'] = tdo.split(len(tdo)-maxbits)
            if _promise:
                #print("SPLITTING", _promise, "INTO")
                _promise, kwargs['_promise']\
                    = _promise.split(len(_promise)-maxbits)
                #print("  ", _promise)
                #print("  ", kwargs['_promise'])
            #print(kwargs)
            #print()
            p = primgen(*args, **kwargs)
            primitives.append(p)

        if count%maxbits:
            kwargs['count'] = count%maxbits
            if istms:
                kwargs['tms']= tms
            if istdi:
                kwargs['tdi'] = tdi
            if istdo:
                kwargs['tdo'] = tdo
            if _promise:
                kwargs['_promise'] = _promise

            #print(kwargs)
            p = primgen(*args, **kwargs)
            primitives.append(p)

        return primitives
