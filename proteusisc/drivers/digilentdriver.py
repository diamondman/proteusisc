#-*- coding: utf-8 -*-
"""
    digilentdriver
    ~~~~~~~~~~~~~~

    Digilent driver for Linux USB JTAG controller

    :copyright: (c) 2014 by Jessy Diamond Exum
    :license: Pending, see LICENSE for more details.
"""

import struct
from time import time

from proteusisc.jtagUtils import blen2Blen, buff2Blen,\
    build_byte_align_buff
from proteusisc.cabledriver import CableDriver
from proteusisc.primitive import Level1Primitive, Executable
from proteusisc.bittypes import ConstantBitarray, NoCareBitarray,\
    CompositeBitarray, bitarray, PreferFalseBitarray
from proteusisc.contracts import NOCARE, ZERO, ONE, CONSTANT, ARBITRARY
from proteusisc.errors import JTAGEnableFailedError,\
    JTAGAlreadyEnabledError, JTAGControlError, JTAGNotEnabledError

#Controller documentation available at
#http://diamondman.github.io/Adapt/cable_digilent_adept.html
#This document is not complete and will evolve as Digilent adds
#new features to the protocol. Please report any issues.
#
#CONTROL MESSAGES:
_CMSG_PROD_NAME = 0xE1
_CMSG_USER_NAME = 0xE2
_CMSG_SERIAL_NO = 0xE4
_CMSG_FW_VER    = 0xE6
_CMSG_DEV_CAPS  = 0xE7
_CMSG_OEM_SEED  = 0xE8
_CMSG_PROD_ID   = 0xE9
_CMSG_OEM_CHECK = 0xEC

#SZ:CT:RQ:00:{Parameters to the request if any}
#   SZ: Length of bulk packet minus 1.
#   CT: Category or request. Category 0x02 appears to be JTAG.
#   RQ: Request Code
#
#BULK MSG PARAMS (Min 1 byte each):
# XX:XX:XX:XX: Transaction count in bits (4 bytes). Little Engian.
# RV: Should return TDO data (Boolean). Little Endian.
# MS: TMS VALUE (Boolean)
# DI: TDI VALUE (Boolean)
# DO: TDO VALUE (Boolean)
# CK: TCK VALUE (Boolean)
# SP: SPEED in Bits/Second
_BMSG_ENABLE_JTAG         = b'\x03\x02\x00\x00'       # NO PARAMS
_BMSG_DISABLE_JTAG        = b'\x03\x02\x01\x00'       # NO PARAMS
_BMSG_PORT_INFO           = b'\x04\x02\x02\x00'       # ??
_BMSG_SET_SPEED           = b'\x07\x02\x03\x00%b'     # SP:SP:SP:SP
_BMSG_GET_SPEED           = b'\x03\x02\x04\x00'       # NO PARAMS
_BMSG_SET_TMS_TDI_TDO     = b'\x06\x02\x05\x00%c%c%c' # MS:DI:DO
_BMSG_GET_TMS_TDI_TDO_TCK = b'\x03\x02\x06\x00'       # NO PARAMS
_BMSG_CLOCK_TICK          = b'\x09\x02\x07\x00%c%c%b' # MS:DI:XX:XX:XX:XX
_BMSG_WRITE_TDI           = b'\x09\x02\x08\x00%c%c%b' # RV:MS:XX:XX:XX:XX
_BMSG_READ_TDO            = b'\x09\x02\x09\x00%c%c%b' # MS:DI:XX:XX:XX:XX
_BMSG_WRITE_TMS_TDI       = b'\x08\x02\x0A\x00%c%b'   # RV:XX:XX:XX:XX
_BMSG_WRITE_TMS           = b'\x09\x02\x0B\x00%c%c%b' # RV:DI:XX:XX:XX:XX

def index_or_default(s):
    try:
        s = s[:s.index(b'\x00')]
    except ValueError:
        pass
    try:
        s = s[:s.index(b'\xFF')]
    except ValueError:
        pass
    return s


##############
# PRIMITIVES #
##############
class DigilentWriteTMSPrimitive(Level1Primitive, Executable):
    _function_name = 'write_tms'
    _driver_function_name = 'write_tms_bits'
    _max_send_bits = 0x5FFFFF
    _max_recv_bits = 504
    _TMS, _TDI, _TDO = ARBITRARY, CONSTANT, CONSTANT
    _args = ['tms']
    _kwargs = {'return_tdo':'tdo', "TDI": 'tdi'}

class DigilentWriteTDIPrimitive(Level1Primitive, Executable):
    _function_name = 'write_tdi'
    _driver_function_name = 'write_tdi_bits'
    _max_send_bits = 0x5FFFFF
    _max_recv_bits = 504
    _TMS, _TDI, _TDO = CONSTANT, ARBITRARY, CONSTANT
    _args = ['tdi']
    _kwargs = {'return_tdo':'tdo', 'TMS': 'tms'}

class DigilentWriteTMSTDIPrimitive(Level1Primitive, Executable):
    _function_name = 'write_tms_tdi'
    _driver_function_name = 'write_tms_tdi_bits'
    _max_send_bits = 0x5FFFFF
    _max_recv_bits = 504
    _TMS, _TDI, _TDO = ARBITRARY, ARBITRARY, CONSTANT
    _args = ['tms', 'tdi']
    _kwargs = {'return_tdo':'tdo'}

class DigilentReadTDOPrimitive(Level1Primitive, Executable):
    _function_name = 'read_tdo'
    _driver_function_name = 'read_tdo_bits'
    _max_send_bits = 504 #63 bytes
    _max_recv_bits = 504 #63 bytes
    _TMS, _TDI, _TDO = CONSTANT, CONSTANT, ONE
    _args = ['count']
    _kwargs = {'TMS':'tms', 'TDI': 'tdi'}

class DigilentClockTickPrimitive(Level1Primitive, Executable):
    _function_name = 'tick_clock'
    _driver_function_name = 'tick_clock'
    _max_send_bits = 0x5FFFFF
    _max_recv_bits = 0
    _TMS, _TDI, _TDO = CONSTANT, CONSTANT, ZERO
    _args = ['count']
    _kwargs = {'TMS': 'tms', 'TDI': 'tdi'}


class DigilentAdeptController(CableDriver):
    _primitives = [DigilentWriteTDIPrimitive, DigilentWriteTMSPrimitive,
                   DigilentWriteTMSTDIPrimitive, DigilentReadTDOPrimitive,
                   DigilentClockTickPrimitive]
    def __init__(self, dev):
        super(DigilentAdeptController, self).__init__(dev)
        h = self._dev.open()

        self.serialNumber = h.controlRead(
            0xC0, _CMSG_SERIAL_NO, 0, 0, 12).decode()
        self.name = index_or_default(
            h.controlRead(0xC0, _CMSG_USER_NAME, 0, 0, 16)).decode()
        #This is probably subtly wrong...
        pidraw = h.controlRead(0xC0, _CMSG_PROD_ID, 0, 0, 4)
        self.productId = (pidraw[3]<<24)|(pidraw[2]<<16)|\
            (pidraw[1]<<8)|pidraw[0] #%08x

        self.productName = index_or_default(
            h.controlRead(0xC0, _CMSG_PROD_NAME, 0, 0, 28)).decode()
        firmwareraw = h.controlRead(0xC0, _CMSG_FW_VER, 0, 0, 2)
        self.firmwareVersion = (firmwareraw[1]<<8)|firmwareraw[0]
        h.close()

        if (self.productId & 0xFF) <= 0x0F:
            self._cmdout_interface = 1
            self._cmdin_interface = 1
            self._datout_interface = 2
            self._datin_interface = 6
        else:
            self._cmdout_interface = 1
            self._cmdin_interface = 2
            self._datout_interface = 3
            self._datin_interface = 4


    def __repr__(self):
        return "%s(%s; Name: %s; SN: %s; FWver: %04x)"%\
            (self.__class__.__name__,
             self.productName,
             self.name,
             self.serialNumber,
             self.firmwareVersion) # pragma: no cover

    def _get_adv_trans_stats(self, cmd, return_tdo=False):
        """Utility function to fetch the transfer statistics for the last
        advanced transfer. Checking the stats appears to sync the
        controller. For details on the advanced transfer please refer
        to the documentation at
        http://diamondman.github.io/Adapt/cable_digilent_adept.html#bulk-requests

        """
        t = time()
        code, res = self.bulkCommand(b'\x03\x02%c\x00'%(0x80|cmd), 10)
        if self._scanchain and self._scanchain._print_statistics:
            print("GET STATS TIME", time()-t)#pragma: no cover
        if len(res) == 4:
            count = struct.unpack('<I', res)[0]
            return count
        elif len(res) == 8:
            written, read =  struct.unpack('<II', res)
            return written, read
        return res

    def _update_scanchain(self, val):
        pass
        #if self._scanchain:
        #    if isinstance(val, bool):
        #        val = ConstantBitarray(, count)
        #    self._scanchain._tap_transition_driver_trigger(val)

    def bulkReadCmd(self, bytecount):
        return self._handle.bulkRead(self._cmdin_interface, bytecount)

    def bulkWriteCmd(self, data):
        return self._handle.bulkWrite(self._cmdout_interface, data)

    def bulkReadData(self, bytecount):
        return self._handle.bulkRead(self._datin_interface, bytecount)

    def bulkWriteData(self, data):
        return self._handle.bulkWrite(self._datout_interface, data)

    def bulkCommand(self, data, reslen=0):
        self.bulkWriteCmd(data)
        return self._read_status(reslen)

    def _read_status(self, reslen=0):
        res = self.bulkReadCmd(2+reslen)
        return res[1], res[2:]

    def bulkCommandDefault(self, data, reslen=0):
        self.bulkWriteCmd(data)
        return self._handle_status_default(reslen)

    def _handle_status_default(self, reslen=0):
        res = self.bulkReadCmd(2+reslen)
        status = res[1]
        if status != 0:
            if status == 4:
                raise JTAGControlError("Controller says jtag disabled.")
            if status == 0x32:
                raise JTAGControlError("Controller says slow down.")
            raise JTAGControlError("Uknown Issue running command: %s",res)
        return res[2:]

    def _read_tdo(self, bitcount):
        tdo_bytes = bytes(self.bulkReadData(blen2Blen(bitcount)+2)[::-1])
        tdo_bits = bitarray()
        tdo_bits.frombytes(tdo_bytes)
        return tdo_bits[(8*len(tdo_bytes)) - bitcount:]

    def _check_jtag(self):
        if not self._jtagon:
            raise JTAGNotEnabledError()

    def jtag_enable(self):
        """
        Enables JTAG output on the controller. JTAG operations executed
        before this function is called will return useless data or fail.

        Usage:
            >>> from proteusisc import getAttachedControllers, bitarray
            >>> c = getAttachedControllers()[0]
            >>> c.jtag_enable()
            >>> c.write_tms_bits(bitarray("001011111"), return_tdo=True)
            >>> c.jtag_disable()
        """
        status, _ = self.bulkCommand(_BMSG_ENABLE_JTAG)
        if status == 0:
            self._jtagon = True
        elif status == 3:
            self._jtagon = True
            raise JTAGAlreadyEnabledError()
        else:
            raise JTAGEnableFailedError("Error enabling JTAG. Error code: %s." %status)

    def jtag_disable(self):
        """
        Disables JTAG output on the controller. JTAG operations executed
        immediately after this function will return useless data or fail.

        Usage:
            >>> from proteusisc import getAttachedControllers, bitarray
            >>> c = getAttachedControllers()[0]
            >>> c.jtag_enable()
            >>> c.write_tms_bits(bitarray("001011111"), return_tdo=True)
            >>> c.jtag_disable()
        """

        if not self._jtagon: return
        status, _ = self.bulkCommand(_BMSG_DISABLE_JTAG)
        if status == 0:
            self._jtagon = False
        elif status == 3:
            raise JTAGControlError("Error Code %s"%status)

        self.close_handle()

    def _get_speed(self):
        if not self._jtagon:
            return None

        speed = self.bulkCommandDefault(_BMSG_GET_SPEED, reslen=4)
        return struct.unpack('<I', speed)[0]

    def _set_speed(self, speed):
        if not self._jtagon:
            return None

        speed = self.bulkCommandDefault(_BMSG_SET_SPEED %
                                        speed.to_bytes(4, 'little'),
                                        reslen=4)
        return struct.unpack('<I', speed)[0]

    def write_tms_bits(self, data, return_tdo=False, TDI=False):
        """
        Command controller to write TMS data (with constant TDI bit)
        to the physical scan chain. Optionally return TDO bits sent
        back from scan the chain.

        Args:
            data - bits to send over TMS line of scan chain (bitarray)
            return_tdo (bool) - return the devices bitarray response
            TDI (bool) - whether TDI should send a bitarray of all 0's
                         of same length as `data` (i.e False) or all 1's
                         (i.e. True)

        Returns:
            None by default or the (bitarray) response of the device
            after receiving data, if return_tdo is True.

        Usage:
            >>> from proteusisc import getAttachedControllers, bitarray
            >>> c = getAttachedControllers()[0]
            >>> c.jtag_enable()
            >>> c.write_tms_bits(bitarray("001011111"), return_tdo=True)
            >>> c.jtag_disable()
        """
        self._check_jtag()
        self._update_scanchain(data)
        self.bulkCommandDefault(_BMSG_WRITE_TMS %
            (return_tdo, TDI, len(data).to_bytes(4, 'little')))
        self.bulkWriteData(build_byte_align_buff(data).tobytes()[::-1])
        tdo_bits = self._read_tdo(len(data)) if return_tdo else None
        self._get_adv_trans_stats(0x0B, return_tdo)
        return tdo_bits

    def write_tdi_bits(self, buff, return_tdo=False, TMS=True):
        """
        Command controller to write TDI data (with constant TMS bit)
        to the physical scan chain. Optionally return TDO bits sent
        back from scan the chain.

        Args:
            data - bits to send over TDI line of scan chain (bitarray)
            return_tdo (bool) - return the devices bitarray response
            TMS (bool) - whether TMS should send a bitarray of all 0's
                         of same length as `data` (i.e False) or all 1's
                         (i.e. True)

        Returns:
            None by default or the (bitarray) response of the device
            after receiving data, if return_tdo is True.

        Usage:
            >>> from proteusisc import getAttachedControllers, bitarray
            >>> c = getAttachedControllers()[0]
            >>> c.jtag_enable()
            >>> c.write_tdi_bits(bitarray("11111"), return_tdo=True)
            >>> c.jtag_disable()
        """
        self._check_jtag()
        tms_bits = bitarray([TMS]*len(buff))
        self._update_scanchain(tms_bits)

        self.bulkCommandDefault(_BMSG_WRITE_TDI %
                    (return_tdo, TMS,  len(buff).to_bytes(4, 'little')))
        self.bulkWriteData(build_byte_align_buff(buff).tobytes()[::-1])
        tdo_bits = self._read_tdo(len(buff)) if return_tdo else None
        self._get_adv_trans_stats(0x08, return_tdo)
        return tdo_bits

    def write_tms_tdi_bits(self, tmsdata, tdidata, return_tdo=False):
        """
        Command controller to write arbitrary TDI and TMS data to the
        physical scan chain. Optionally return TDO bits sent back
        from the scan chain.

        Args:
            tmsdata - bits to send over TMS line of scan chain (bitarray)
                      must be the same length ad tdidata
            tdidata - bits to send over TDI line of scan chain (bitarray)
                      must be the same length ad tmsdata
            return_tdo (bool) - return the devices bitarray response

        Returns:
            None by default or the (bitarray) response of the device
            after receiving data, if return_tdo is True.

        Usage:
            >>> from proteusisc import getAttachedControllers, bitarray
            >>> c = getAttachedControllers()[0]
            >>> c.jtag_enable()
            >>> c.write_tms_tdi_bits(bitarray("00001"),
                                     bitarray("11111"), return_tdo=True)
            >>> c.jtag_disable()
        """
        self._check_jtag()
        if len(tmsdata) != len(tdidata):
            raise Exception("TMSdata and TDIData must be the same length")
        self._update_scanchain(tmsdata)
        count = len(tmsdata)

        t = time()
        outdata = bitarray([val for pair in zip(tmsdata, tdidata)
                            for val in pair])
        outdata = build_byte_align_buff(outdata).tobytes()[::-1]

        if self._scanchain and self._scanchain._print_statistics:
            print("TDI/TDI DATA PREP TIME", time()-t)#pragma: no cover
            t = time()

        self.bulkCommandDefault(_BMSG_WRITE_TMS_TDI % \
                  (return_tdo, count.to_bytes(4, 'little')))
        self.bulkWriteData(outdata)

        if self._scanchain and self._scanchain._print_statistics:
            print("TRANSFER TIME", time()-t)
            t = time()

        tdo_bits = self._read_tdo(count) if return_tdo else None

        if self._scanchain and self._scanchain._print_statistics:
            print("TDO READ TIME", time()-t)#pragma: no cover

        self._get_adv_trans_stats(0x0A, return_tdo)
        return tdo_bits

    def read_tdo_bits(self, count, TMS=True, TDI=False):
        """
        Command controller to issue [count] bit transfers to the physicsl
        scan chain, with a constant TMS and TDI value, and reading back
        the returned TDO bits.

        Args:
            count (int) - Number of bits to read from TDO and write
                          to TMS/TDI
            TMS (bool) - constant value to write to TMS for each bit read
                         from TDO.
            TDI (bool) - constant value to write to TDI for each bit read
                         from TDO.

        Returns:
            Returns the response (bitarray) from the physical scanchain's
            TDO line.

        Usage:
            >>> from proteusisc import getAttachedControllers
            >>> c = getAttachedControllers()[0]
            >>> c.jtag_enable()
            >>> data = c.read_tdo_bits(32)
            >>> c.jtag_disable()
        """
        self._check_jtag()
        self._update_scanchain(bool(TMS))

        self.bulkCommandDefault(
            _BMSG_READ_TDO % (TMS, TDI, count.to_bytes(4, 'little')))
        res = self._read_tdo(count)
        self._get_adv_trans_stats(_BMSG_READ_TDO[2], True)
        return res

    def tick_clock(self, count, TMS=True, TDI=False):
        self._check_jtag()
        self._update_scanchain(bool(TMS))

        self.bulkCommandDefault(_BMSG_CLOCK_TICK %\
                                (TMS, TDI, count.to_bytes(4, 'little')))
        self._get_adv_trans_stats(_BMSG_CLOCK_TICK[2], True)

__filter__ = [((0x1443, None),DigilentAdeptController)]
