import math
import time
import struct
from bitarray import bitarray

from . import jtagDeviceDescription
from .jtagStateMachine import JTAGStateMachine
from .primative import Level1Primative, Level2Primative
from .primative_defaults import ChangeTAPStatePrimative,\
    LoadIRPrimative, ReadDRPrimative,\
    LoadDRPrimative, LoadReadRegisterPrimative,\
    SleepPrimative
from .jtagDevice import JTAGDevice
from .command_queue import CommandQueue
from .cabledriver import InaccessibleController
from .errors import DevicePermissionDeniedError, JTAGAlreadyEnabledError
from .jtagUtils import NULL_ID_CODES, pstatus

class JTAGScanChain(object):
    def gen_prim_adder(self, cls_):
        if not hasattr(self, cls_._function_name):
            def adder(*args, **kwargs):
                self._command_queue.append(cls_(*args, **kwargs))
                #res = self._command_queue.get_return()
                #print(" "*3, cls_.__name__, "returns", res)
                #return res
            setattr(self, cls_._function_name, adder)
            self._lv2_primatives[cls_._function_name] = cls_
            #print("Adding %s->%s OK"%(cls_._function_name, cls_))
            return True
        #print("Adding %s FAIL"%cls_)
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
        self.get_descriptor_for_idcode = jtagDeviceDescription.get_descriptor_for_idcode

        if isinstance(controller, InaccessibleController):
            raise DevicePermissionDeniedError()
        self._controller = controller
        self._controller._scanchain = self #This might necessitate a factory

        self._command_queue = CommandQueue(self)

        self._lv1_primatives = []
        self._lv2_primatives = {}
        for primative in self._controller._primatives:
            if issubclass(primative, Level2Primative):
                if not self.gen_prim_adder(primative):
                    raise Exception("Failed adding primative %s, primative with name %s "\
                                        "already exists on scanchain"%\
                                        (primative, primative._function_name))
            elif issubclass(primative, Level1Primative):
                self._lv1_primatives.append(primative)
            else:
                print("WTF", primative)

        for primative_cls in [ChangeTAPStatePrimative,
                              LoadIRPrimative,
                              ReadDRPrimative,
                              LoadDRPrimative,
                              LoadReadRegisterPrimative,
                              SleepPrimative]:
            self.gen_prim_adder(primative_cls)

    def snapshot_queue(self):
        return self._command_queue.snapshot()

    def queue_command(self, prim):
        self._command_queue.append(prim)

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
