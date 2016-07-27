#-*- coding: utf-8 -*-
"""
    digilentdriver
    ~~~~~~~~~~~~~~

    Digilent driver for Linux USB JTAG controller

    :copyright: (c) 2014 by Jessy Diamond Exum
    :license: Pending, see LICENSE for more details.
"""

from bitarray import bitarray

from proteusisc.jtagUtils import blen2Blen, buff2Blen,\
    build_byte_align_buff
from proteusisc.cabledriver import CableDriver
from proteusisc.primative import Level1Primative,\
    Executable, DOESNOTMATTER, ZERO, ONE, CONSTANT, SEQUENCE
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
# XX:XX:XX:XX: Transaction count in bits (4 bytes)
# MS: TMS VALUE (Boolean)
# DI: TDI VALUE (Boolean)
# DO: TDO VALUE (Boolean)
# CK: TCK VALUE (Boolean)
# RV: Should return TDO data (Boolean)
_BMSG_ENABLE_JTAG         = b'\x03\x02\x00\x00' # NO PARAMS
_BMSG_DISABLE_JTAG        = b'\x03\x02\x01\x00' # NO PARAMS
_BMSG_PORT_INFO           = b'\x04\x02\x02\x00' #
_BMSG_SET_SPEED           = b'\x07\x02\x03\x00' # SP:SP:SP:SP Speed in bps
_BMSG_GET_SPEED           = b'\x03\x02\x04\x00' # NO PARAMS
_BMSG_SET_TMS_TDI_TDO     = b'\x06\x02\x05\x00' # MS:DI:DO
_BMSG_GET_TMS_TDI_TDO_TCK = b'\x03\x02\x06\x00' # NO PARAMS
_BMSG_CLOCK_TICK          = b'\x09\x02\x07\x00' # MS:DI:XX:XX:XX:XX
_BMSG_WRITE_TDI           = b'\x09\x02\x08\x00' # RV:MS:XX:XX:XX:XX
_BMSG_READ_TDO            = b'\x09\x02\x09\x00' # MS:DI:XX:XX:XX:XX
_BMSG_WRITE_TMS_TDI       = b'\x08\x02\x0A\x00' # RV:XX:XX:XX:XX
_BMSG_WRITE_TMS           = b'\x09\x02\x0B\x00' # RV:DI:XX:XX:XX:XX


def data2translen(data):
    return b"".join([bytes([(len(data)>>(8*i))&0xff]) for i in range(4)])


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
# PRIMATIVES #
##############
class DigilentWriteTMSPrimative(Level1Primative, Executable):
    _driver_function_name = 'write_tms_bits'
    """TMS, TDI, TDO"""
    _effect = [SEQUENCE, CONSTANT, CONSTANT]
    def __init__(self, count, tms, tdi, tdo):
        self.count, self.tms, self.tdi, self.tdo = count, tms, tdi, tdo
    def _get_args(self):
        return [self.tms], {'return_tdo':self.tdo, 'TDI': self.tdi}

class DigilentWriteTDIPrimative(Level1Primative, Executable):
    _driver_function_name = 'write_tdi_bits'
    """TMS, TDI, TDO"""
    _effect = [CONSTANT, SEQUENCE, CONSTANT]
    def __init__(self, count, tms, tdi, tdo):
        self.count, self.tms, self.tdi, self.tdo = count, tms, tdi, tdo
    def _get_args(self):
        return [self.tdi], {'return_tdo':self.tdo, 'TMS': self.tms}

class DigilentWriteTMSTDIPrimative(Level1Primative, Executable):
    _driver_function_name = 'write_tms_tdi_bits'
    """TMS, TDI, TDO"""
    _effect = [SEQUENCE, SEQUENCE, CONSTANT]
    def __init__(self, count, tms, tdi, tdo):
        self.count, self.tms, self.tdi, self.tdo = count, tms, tdi, tdo
    def _get_args(self):
        return [self.tms, self.tdi], {'return_tdo':self.tdo}

class DigilentReadTDOPrimative(Level1Primative, Executable):
    _driver_function_name = 'read_tdo_bits'
    """TMS, TDI, TDO"""
    _effect = [CONSTANT, CONSTANT, ONE]
    def __init__(self, count, tms, tdi, tdo):
        self.count, self.tms, self.tdi, self.tdo = count, tms, tdi, tdo
    def _get_args(self):
        return [self.count], {'TMS': self.tms, 'TDI': self.tdi}

class LIESTDIHighPrimative(Level1Primative, Executable):
    _driver_function_name = 'lies_lies'
    """TMS, TDI, TDO"""
    _effect = [CONSTANT, ONE, ONE]
    def __init__(self, count, tms, tdi, tdo):
        self.count, self.tms, self.tdi, self.tdo = count, tms, tdi, tdo
    def _get_args(self):
        return [], {}


class DigilentAdeptController(CableDriver):
    _primatives = [DigilentWriteTDIPrimative, DigilentWriteTMSPrimative,
                   DigilentWriteTMSTDIPrimative, DigilentReadTDOPrimative,
                   LIESTDIHighPrimative]
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
             self.firmwareVersion)


    def _get_adv_trans_stats(self, cmd, return_tdo=False):
        """
        Utility function to fetch the transfer statistics for the
        last advanced transfer. For details on the advanced transfer
        please refer to the documentation at
        http://diamondman.github.io/Adapt/cable_digilent_adept.html#bulk-requests
        """

        self._handle.bulkWrite(self._cmdout_interface,
                               bytes([0x03, 0x02, 0x80|cmd, 0x00]))
        return self._handle.bulkRead(self._cmdin_interface,
                                     10 if return_tdo else 6)


    def jtag_enable(self):
        """
        Enables JTAG output on the controller. JTAG operations executed
        before this function is called will return useless data or fail.

        Usage:
            >>> from proteusisc import getAttachedControllers
            >>> from bitarray import bitarray
            >>> c = getAttachedControllers()[0]
            >>> c.jtag_enable()
            >>> c.write_tms_bits(bitarray("111110100"), return_tdo=True)
            >>> c.jtag_disable()
        """
        h_ = self._handle
        h_.bulkWrite(self._cmdout_interface, _BMSG_ENABLE_JTAG)
        res = h_.bulkRead(self._cmdin_interface, 2)
        status_code = res[1]
        if status_code == 0:
            self._jtagon = True
        elif status_code == 3:
            self._jtagon = True
            raise JTAGAlreadyEnabledError()
        else:
            raise JTAGEnableFailedError("Error enabling JTAG. Error code: %s." %res[1])


    def jtag_disable(self):
        """
        Disables JTAG output on the controller. JTAG operations executed
        immediately after this function will return useless data or fail.

        Usage:
            >>> from proteusisc import getAttachedControllers
            >>> from bitarray import bitarray
            >>> c = getAttachedControllers()[0]
            >>> c.jtag_enable()
            >>> c.write_tms_bits(bitarray("111110100"), return_tdo=True)
            >>> c.jtag_disable()
        """

        if not self._jtagon: return
        h = self._handle
        h.bulkWrite(self._cmdout_interface, _BMSG_DISABLE_JTAG)
        res = h.bulkRead(self._cmdin_interface, 2)
        status_code = res[1]
        if status_code == 0:
            self._jtagon = False
        elif status_code == 3:
            raise JTAGControlError("Error Code %s"%status_code)


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
            >>> from proteusisc import getAttachedControllers
            >>> from bitarray import bitarray
            >>> c = getAttachedControllers()[0]
            >>> c.jtag_enable()
            >>> c.write_tms_bits(bitarray("111110100"), return_tdo=True)
            >>> c.jtag_disable()
        """
        if not self._jtagon:
            raise JTAGNotEnabledError()
        if self._scanchain:
            self._scanchain._tap_transition_driver_trigger(data)


        self._handle.bulkWrite(self._cmdout_interface,
                               _BMSG_WRITE_TMS +\
                               bytes([return_tdo, TDI]) +\
                               data2translen(data))
        res = self._handle.bulkRead(self._cmdin_interface, 2)
        if res[1] != 0:
            raise JTAGControlError("Uknown Issue writing TMS bits: %s",
                                   res)

        self._handle.bulkWrite(self._datout_interface,
                               build_byte_align_buff(data).tobytes()[::-1]
        )

        tdo_bits = None
        if return_tdo:
            tdo_bytes = self._handle.bulkRead(self._datin_interface,
                                        buff2Blen(data))[::-1]
            tdo_bits = bitarray()
            for byte_ in tdo_bytes:
                tdo_bits.extend(bin(byte_)[2:].zfill(8))
            tdo_bits = tdo_bits[len(tdo_bits)-len(data):]


        self._get_adv_trans_stats(0x0B, return_tdo)

        return tdo_bits


    def write_tdi_bits(self, buff, return_tdo=False, TMS=False):
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
            >>> from proteusisc import getAttachedControllers
            >>> from bitarray import bitarray
            >>> c = getAttachedControllers()[0]
            >>> c.jtag_enable()
            >>> c.write_tdi_bits(bitarray("11111"), return_tdo=True)
            >>> c.jtag_disable()
        """
        if not self._jtagon:
            raise JTAGNotEnabledError()
        tms_bits = bitarray(('1' if TMS else '0')*len(buff))
        if self._scanchain:
            self._scanchain._tap_transition_driver_trigger(tms_bits)
        self._handle.bulkWrite(self._cmdout_interface,
                               _BMSG_WRITE_TDI +\
                               b"".join([bytes([(len(buff)>>(8*i))&0xff]) for
                                         i in range(4)]))
        res = self._handle.bulkRead(self._cmdin_interface, 2)
        if res[1] != 0:
            raise JTAGControlError("Uknown Issue writing TDI bits: %s",
                                   res)

        self._handle.bulkWrite(self._datout_interface,
                               build_byte_align_buff(buff).tobytes()[::-1])

        tdo_bits = None
        if return_tdo is True:
            tdo_bytes = self._handle.bulkRead(self._datin_interface,
                                              buff2Blen(buff))[::-1]
            tdo_bits = bitarray()
            for byte_ in tdo_bytes:
                tdo_bits.extend(bin(byte_)[2:].zfill(8))

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
            >>> from proteusisc import getAttachedControllers
            >>> from bitarray import bitarray
            >>> c = getAttachedControllers()[0]
            >>> c.jtag_enable()
            >>> c.write_tms_tdi_bits(bitarray("00001"),
                                     bitarray("11111"), return_tdo=True)
            >>> c.jtag_disable()
        """
        if not self._jtagon:
            raise JTAGNotEnabledError()
        if len(tmsdata) != len(tdidata):
            raise Exception("TMSdata and TDIData must be the same length")
        if self._scanchain:
            self._scanchain._tap_transition_driver_trigger(tmsdata)

        self._handle.bulkWrite(self._cmdout_interface,
                               _BMSG_WRITE_TMS_TDI +\
                               bytes([return_tdo]) +\
                               data2translen(tdidata))
        res = self._handle.bulkRead(self._cmdin_interface, 2)
        if res[1] != 0:
            raise JTAGControlError("Uknown Issue writing TMS bits: %s", res)

        data = bitarray([val for pair in zip(tmsdata, tdidata)
                         for val in pair])
        self._handle.bulkWrite(self._datout_interface,
                               build_byte_align_buff(data).tobytes()[::-1])

        tdo_bits = None
        if return_tdo:
            tdo_bytes = self._handle.bulkRead(self._datin_interface,
                                              buff2Blen(data))[::-1]
            tdo_bits = bitarray()
            for byte_ in tdo_bytes:
                tdo_bits.extend(bin(byte_)[2:].zfill(8))

        self._get_adv_trans_stats(0x0A, return_tdo)

        return tdo_bits

    def read_tdo_bits(self, count, TMS=False, TDI=False):
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
            >>> from bitarray import bitarray
            >>> c = getAttachedControllers()[0]
            >>> c.jtag_enable()
            >>> data = c.read_tdo_bits(32)
            >>> c.jtag_disable()
        """
        if not self._jtagon:
            raise JTAGNotEnabledError()
        if self._scanchain:
            bits = bitarray(('1' if TMS else '0')*count)
            self._scanchain._tap_transition_driver_trigger(bits)

        #START REQUEST
        self._handle.bulkWrite(self._cmdout_interface,
                               _BMSG_READ_TDO +\
                               bytes([TMS, TDI]) +\
                               b"".join([bytes([(count>>(8*i))&0xff])
                                         for i in range(4)]))
        res = self._handle.bulkRead(self._cmdin_interface, 2)
        if res[1] != 0:
            raise JTAGControlError("Uknown Issue reading TDO bits: %s", res)

        #READ TDO DATA BACK
        tdo_bytes = self._handle.bulkRead(self._datin_interface,
                                          blen2Blen(count))[::-1]
        tdo_bits = bitarray()
        for byte_ in tdo_bytes:
            tdo_bits.extend(bin(byte_)[2:].zfill(8))

        #GET BACK STATS
        self._get_adv_trans_stats(0x09, True)

        return tdo_bits



__filter__ = [((0x1443, None),DigilentAdeptController)]
