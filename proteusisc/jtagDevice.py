import struct
import time
import sys

from bitarray import bitarray

from .primative_defaults import RunInstruction
from .jtagDeviceDescription import JTAGDeviceDescription
from .jtagUtils import pstatus

class JTAGDeviceBase(object):
    def __init__(self, chain, idcode):
        self._chain = chain
        self._current_DR = None

        fail = False
        if isinstance(idcode, int):
            if len(bin(idcode)[2:]) > 32:
                fail = True
            else:
                self._id = idcode
        elif isinstance(idcode, bitarray):
            if len(idcode) is not 32:
                fail = True
            else:
                self._id = struct.unpack("<L", idcode.tobytes()[::-1])[0]
        elif isinstance(idcode, str):
            if len(idcode) is not 4:
                fail = True
            else:
                self._id = struct.unpack("<L", idcode[::-1])[0]
        else:
            raise ValueError("JTAGDevice idcode parameter must be an int or "
                             "string of length 4. (Invalid Type: %s)"%type(idcode))
        if fail:
            raise ValueError("JTAGDevice idcode parameter must be a 32 "
                             "bit int, a string of length 4, or a bitarray "
                             "of 32 bits (%s len: %s)"%(idcode,len(idcode)))

        if not self._id & 1:
            raise Exception("Invalid JTAG ID Code: LSB must be 1 (IEEE 1149.1)")

        self._desc = None

    def run_tap_instruction(self, *args, **kwargs):
        return self._chain.queue_command(
            RunInstruction(self, *args, **kwargs))

    @property
    def chain_index(self):
        return self._chain._devices.index(self) if self._chain else -1

    def __repr__(self):
        devnum = self.chain_index
        devname = "?"#self._desc._device_name if self._desc else "?"
        return "<D%s: %s>"%(devnum, devname)

class JTAGDevice(JTAGDeviceBase):
    def __init__(self, chain, idcode):
        super(JTAGDevice, self).__init__(chain, idcode)
        self._desc = self._chain.get_descriptor_for_idcode(self._id)
