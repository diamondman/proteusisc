import struct

from bitarray import bitarray

from .jtagDeviceDescription import JTAGDeviceDescription

class JTAGDeviceBase(object):
    def gen_prim_adder(self, cls_):
        if not hasattr(self, cls_._function_name):
            def adder(*args, **kwargs):
                return self._chain.queue_command(cls_(dev=self,
                                                      _chain=self._chain,
                                                      *args, **kwargs))
            setattr(self, cls_._function_name, adder)
            return True
        return False

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
            raise ValueError("JTAGDevice idcode parameter must be an int "
                             "or string of length 4. (Invalid Type: %s)"%\
                             type(idcode))
        if fail:
            raise ValueError("JTAGDevice idcode parameter must be a 32 "
                             "bit int, a string of length 4, or a "
                             "bitarray of 32 bits (%s len: %s)"%\
                             (idcode,len(idcode)))

        if not self._id & 1:
            raise Exception("Invalid JTAG ID Code: LSB must be 1 "
                            "(IEEE 1149.1)")

        self._desc = None

        for func_name, prim in self._chain._device_primitives.items():
            if not self.gen_prim_adder(prim):
                raise Exception("Failed adding primitive %s, "\
                                "primitive with name %s "\
                                "already exists on device"%\
                                (prim, prim._function_name))

    @property
    def chain_index(self):
        if self._chain and self in self._chain._devices:
            return self._chain._devices.index(self)
        return -1

    def __repr__(self):
        devnum = self.chain_index
        devname = "?"#self._desc._device_name if self._desc else "?"
        return "<D%s: %s>"%(devnum, devname)

class JTAGDevice(JTAGDeviceBase):
    def __init__(self, chain, idcode):
        super(JTAGDevice, self).__init__(chain, idcode)
        self._desc = self._chain.get_descriptor_for_idcode(self._id)
