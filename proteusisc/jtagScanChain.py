import math
import time
import struct
from functools import partial
from bitarray import bitarray

from . import jtagDeviceDescription
from .jtagStateMachine import JTAGStateMachine
from .primitive import Primitive, DeviceTarget, DataRW, Level1Primitive
from .primitive_defaults import RunInstruction,\
    TransitionTAP, RWReg, RWDR, RWIR, Sleep
from .primitive_defaults import RWDevDR, RWDevIR
from .jtagDevice import JTAGDevice
from .command_queue import CommandQueue
from .cabledriver import InaccessibleController
from .errors import DevicePermissionDeniedError, JTAGAlreadyEnabledError,\
    JTAGTooManyDevicesError
from .jtagUtils import NULL_ID_CODES

class JTAGScanChain(object):
    def gen_prim_adder(self, cls_):
        if not hasattr(self, cls_._function_name):
            def adder(*args, **kwargs):
                return self.queue_command(cls_(_chain=self, *args,
                                               **kwargs))
            setattr(self, cls_._function_name, adder)
            return True
        return False

    def __init__(self, controller,
                 device_initializer=\
                 lambda sc, idcode: JTAGDevice(sc,idcode),
                 ignore_jtag_enabled=False, debug=False):
        self._debug = debug
        self._devices = []
        self._hasinit = False
        self._sm = JTAGStateMachine()
        self._ignore_jtag_enabled = ignore_jtag_enabled

        self.initialize_device_from_id = device_initializer
        self.get_descriptor_for_idcode = \
                    jtagDeviceDescription.get_descriptor_for_idcode

        if isinstance(controller, InaccessibleController):
            raise DevicePermissionDeniedError()
        self._controller = controller
        #This might necessitate a factory
        self._controller._scanchain = self

        self._command_queue = CommandQueue(self)

        default_prims = {RunInstruction,
                         TransitionTAP, RWReg, RWDR, RWIR, Sleep,
                         RWDevDR, RWDevIR}
        self._chain_primitives = {}
        self._device_primitives = {}
        self._lv1_chain_primitives = []

        for prim in default_prims:
            assert issubclass(prim, Primitive)
            if issubclass(prim, DeviceTarget):
                self._device_primitives[prim._function_name] = prim
            else:
                self._chain_primitives[prim._function_name] = prim

        for prim in self._controller._primitives:
            if not issubclass(prim, Primitive):
                raise Exception("Registered Controller Prim has "
                                "unknown type. (%s)"%prim)
            if issubclass(prim, DeviceTarget):
                self._device_primitives[prim._function_name] = prim
            else:
                self._chain_primitives[prim._function_name] = prim
                if issubclass(prim, Level1Primitive):
                    self._lv1_chain_primitives.append(prim)

        for func_name, prim in self._chain_primitives.items():
            if not self.gen_prim_adder(prim):
                raise Exception("Failed adding primitive %s, "\
                                "primitive with name %s "\
                                "already exists on scanchain"%\
                                (prim, prim._function_name))

    def __repr__(self):
        return "<JTAGScanChain>"

    def snapshot_queue(self):
        return self._command_queue.snapshot()

    def queue_command(self, prim):
        self._command_queue.append(prim)
        return prim.get_promise()

    def get_prim(self, name):
        res = self._chain_primitives.get(name)
        if res:
            return res
        return self._device_primitives[name]

    def init_chain(self):
        if not self._hasinit:
            self._hasinit = True
            self._devices = []

            self.jtag_enable()
            while True:
                # pylint: disable=no-member
                idcode = self.rw_dr(bitcount=32, read=True,
                                    lastbit=False)()
                if idcode in NULL_ID_CODES: break
                dev = self.initialize_device_from_id(self, idcode)
                if self._debug:
                    print(dev)
                self._devices.append(dev)
                if len(self._devices) >= 128:
                    raise JTAGTooManyDevicesError("This is an arbitrary "
                        "limit to deal with breaking infinite loops. If "
                        "you have more devices, please open a bug")

            self.jtag_disable()

            #The chain comes out last first. Reverse it to get order.
            self._devices.reverse()

    def flush(self):
        self._command_queue.flush()

    def jtag_disable(self):
        #self.flush()
        self._sm.reset()
        self._command_queue.reset()
        self._controller.jtag_disable()

    def jtag_enable(self):
        self._sm.reset()
        self._command_queue.reset()
        try:
            self._controller.jtag_enable()
        except JTAGAlreadyEnabledError as e:
            if not self._ignore_jtag_enabled:
                raise e

    def _tap_transition_driver_trigger(self, bits):
        statetrans = [self._sm.state]
        for bit in bits[::-1]:
            self._sm.transition_bit(bit)
            statetrans.append(self._sm.state)

    def get_compatible_lv1_prims(self, reqef):
        styles = {0:'\033[92m', #GREEN
                  1:'\033[93m', #YELLOW
                  2:'\033[91m'} #RED
        possible_prims = []
        for prim in self._lv1_chain_primitives:
            efstyledstr = ''
            ef = prim.get_effect()

            worststyle = 0
            for i in range(3):
                curstyle = 0
                if not ef[i].satisfies(reqef[i]):
                    #if (ef[i]&reqef[i]) is not reqef[i]:
                    curstyle = 1 if ef[i].constant else 2

                efstyledstr += "%s%s "%(styles.get(curstyle), ef[i])
                if curstyle > worststyle:
                    worststyle = curstyle

            if worststyle == 0:
                possible_prims.append(prim)
            if self._debug:
                print(" ",efstyledstr, styles.get(worststyle)+\
                      prim.__name__+"\033[0m")

        if not len(possible_prims):
            raise Exception('Unable to match Primative to lower '
                            'level Primative.')
        return possible_prims

    def get_best_lv1_prim(self, reqef):
        possible_prims = self.get_compatible_lv1_prims(reqef)
        best_prim = possible_prims[0]
        for prim in possible_prims[1:]:
            if sum((e.score for e in prim.get_effect())) <\
               sum((e.score for e in best_prim.get_effect())):
                best_prim = prim
        if self._debug:
            print("PICKED", best_prim, "\n")
        return best_prim

    def get_fitted_lv1_prim(self, reqef):
        """
             request
        r   - A C 0 1
        e -|? ! ! ! !
        s A|? ✓ ✓ 0 1 Check this logic
        u C|? m ✓ 0 1
        l 0|? M M 0 !
        t 1|? M M ! 1

        - = No Care
        A = arbitrary
        C = Constant
        0 = ZERO
        1 = ONE

        ! = ERROR
        ? = NO CARE RESULT
        ✓ = Pass data directly
        m = will require reconfiguring argument and using multiple of prim
        M = Requires using multiple of several prims to satisfy requirement
        """
        prim = self.get_best_lv1_prim(reqef)

        return partial(prim, _chain=self, reqef=reqef)
