import math
import time
import struct
from bitarray import bitarray

from . import jtagDeviceDescription
from .jtagStateMachine import JTAGStateMachine
from .primitive import Primitive, DeviceTarget, DataRW
from .primitive_defaults import RunInstruction,\
    TransitionTAP, RWReg, RWDR, RWIR, Sleep
from .primitive_defaults import RWDevDR, RWDevIR
from .jtagDevice import JTAGDevice
from .command_queue import CommandQueue
from .cabledriver import InaccessibleController
from .errors import DevicePermissionDeniedError, JTAGAlreadyEnabledError
from .jtagUtils import NULL_ID_CODES, pstatus

class JTAGScanChain(object):
    def gen_prim_adder(self, cls_):
        if not hasattr(self, cls_._function_name):
            def adder(*args, **kwargs):
                return self.queue_command(cls_(*args, **kwargs))
            setattr(self, cls_._function_name, adder)
            return True
        return False

    def __init__(self, controller,
                 device_initializer=\
                 lambda sc, idcode: JTAGDevice(sc,idcode),
                 ignore_jtag_enabled=False):
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

        for prim in default_prims:
            assert issubclass(prim, Primitive)
            if issubclass(prim, DeviceTarget):
                self._device_primitives[prim._function_name] = prim
            else:
                self._chain_primitives[prim._function_name] = prim

        for prim in self._controller._primitives:
            if not issubclass(prim, Primitive):
                raise Exception("Registered Controller Prim has "
                                "unknown type. (%s)"%primitive)
            if issubclass(prim, DeviceTarget):
                self._device_primitives[prim._function_name] = prim
            else:
                self._chain_primitives[prim._function_name] = prim

        for func_name, prim in self._chain_primitives.items():
            if not self.gen_prim_adder(prim):
                raise Exception("Failed adding primitive %s, "\
                                "primitive with name %s "\
                                "already exists on scanchain"%\
                                (prim, prim._function_name))

    def snapshot_queue(self):
        return self._command_queue.snapshot()

    def queue_command(self, prim):
        self._command_queue.append(prim)
        res = None
        if isinstance(prim, DataRW):
            res = prim.get_promise()
        return res

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
                idcode_str = self.read_dr(32)
                if idcode_str in NULL_ID_CODES: break
                dev = self.initialize_device_from_id(self, idcode_str)
                self._devices.append(dev)

            self.flush()
            self.jtag_disable()

            #The chain comes out last first. Reverse it to get order.
            self._devices.reverse()

    def flush(self):
        self._command_queue.flush()

    def jtag_disable(self):
        self.flush()
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
