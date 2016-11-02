#-*- coding: utf-8 -*-
"""
    digilentdriver
    ~~~~~~~~~~~~~~

    Digilent driver for Linux USB JTAG controller

    :copyright: (c) 2014 by Jessy Diamond Exum
    :license: Pending, see LICENSE for more details.
"""
from time import time
import math
import numbers

from proteusisc.cabledriver import CableDriver
from proteusisc.primitive import Level1Primitive,\
    Level2Primitive, Level3Primitive, Executable
from proteusisc.contracts import NOCARE, ZERO, ONE, CONSTANT, ARBITRARY
from proteusisc.errors import JTAGEnableFailedError,\
    JTAGAlreadyEnabledError, JTAGNotEnabledError
from proteusisc.bittypes import ConstantBitarray, CompositeBitarray,\
    bitarray
from . import _xpcu1utils

#PROG = 8
#TCK = 4
#TMS = 2
#TDI = 1
#TDO = 1

class XPC1TransferPrimitive(Level1Primitive, Executable):
    _function_name = 'transfer_bits'
    _driver_function_name = 'transfer_bits'
    _max_send_bits = 0xFFFFFF+1
    _max_recv_bits = 0xFFFFFF+1
    _TMS, _TDI, _TDO = ARBITRARY, ARBITRARY, ARBITRARY
    _args = ['count']
    _kwargs = {'TMS': 'tms', 'TDI': 'tdi', 'TDO': 'tdo'}

class XilinxPC1Driver(CableDriver):
    _primitives = [XPC1TransferPrimitive]
    def __init__(self, dev):
        super(XilinxPC1Driver, self).__init__(dev)
        h = self._dev.open()

        self.serialNumber = '000000000000'
        self.name = 'PC1_'+self.serialNumber[-4:]
        self.productId = 0

        self.productName = 'Platform Cable 1'
        self.firmwareVersion = 0

        #Physically set the controller Speed
        self.speed = 12000000
        h.close()


    def __repr__(self): #pragma: no cover
        return "%s(%s; Name: %s; SN: %s; FWver: %04x)"%\
                                         (self.__class__.__name__,
                                          self.productName,
                                          self.name,
                                          self.serialNumber,
                                          self.firmwareVersion)

    def jtag_enable(self):
        if self._dev.getProductID() == 0x0D:
            self._handle.claimInterface(0)
            self._handle.setInterfaceAltSetting(0,1)
        self.xpcu_enable_output(True)
        self.xpcu_set_jtag_speed(False)
        self._jtagon = True
        #self.xpcu_enable_cpld_upgrade_mode(True)

    def jtag_disable(self):
        self.xpcu_enable_output(False)
        if self._dev.getProductID() == 0x0D and self._jtagon:
            self._handle.releaseInterface(0)
        self._jtagon = False

        #self.xpcu_enable_cpld_upgrade_mode(False)

    #@profile
    def transfer_bits(self, count, *, TMS=True, TDI=False, TDO=False):
        if not self._jtagon:
            raise JTAGNotEnabledError('JTAG Must be enabled first')
        if count < 1:
            raise ValueError()
        if count > 0xFFFFFF+1:
            raise ValueError("Too many transactions. Max 16777216.")

        if isinstance(TMS, (numbers.Number, bool)):
            TMS = ConstantBitarray(bool(TMS), count)
        if isinstance(TDI, (numbers.Number, bool)):
            TDI = ConstantBitarray(bool(TDI), count)
        if isinstance(TDO, (numbers.Number, bool)):
            bit_return_count = count*bool(TDO)
            TDO = ConstantBitarray(bool(TDO), count)
        else:
            t = time()
            bit_return_count = TDO.count(True)
            if self._scanchain and self._scanchain._print_statistics:
                print("BIT RETURN COUNT CALCULATION TIME", time()-t)\
                    #pragma: no cover

        adjusted_count = math.ceil(count/4)*4
        outbaseindex = 0
        inoffset = 0

        if self._scanchain and self._scanchain._print_statistics:
            print("BIT RETURN COUNT", bit_return_count, "COUNT", count)\
                #pragma: no cover

        itms = TMS.byteiter()
        itdi = TDI.byteiter()
        itdo = TDO.byteiter()

        t = time()
        #Returns int(math.ceil(count/4.0))*2) bytes
        outdata = _xpcu1utils.calc_xfer_payload(count, itms, itdi, itdo)
        if self._scanchain and self._scanchain._print_statistics:
            print("XPCU1 byte blocks C Prepare Time:", time()-t)\
                #pragma: no cover

        return self.xpcu_GPIO_transfer(adjusted_count, outdata,
                    bit_return_count=bit_return_count)

    def transfer_bits_single(self, count, TMS, TDI, TDO=False):
        if not self._jtagon:
            raise JTAGNotEnabledError()
        if isinstance(TMS, (numbers.Number, bool)):
            TMS = bitarray(count*(bool(TMS),))
        if isinstance(TDI, (numbers.Number, bool)):
            TDI = bitarray(count*(bool(TDI),))
        #if isinstance(TDO, (numbers.Number, bool)):
        #    TDO = bitarray(count*(bool(TDO),))
        if self._scanchain:
            self._scanchain._tap_transition_driver_trigger(TMS)
        #self.xpcu_single_read()
        outbits = bitarray()
        TMS.reverse()
        TDI.reverse()

        for bit_num in range(count):
            self.xpcu_single_write(TMS[bit_num], TDI[bit_num])
            if TDO:
                b = self.xpcu_single_read()
                outbits.append(b)

        if outbits:
            outbits.reverse()
            return outbits

    def transfer_bits_single_cpld_upgrade(self, count, TMS, TDI, TDO=False):
        if not self._jtagon:
            raise JTAGNotEnabledError()
        if isinstance(TMS, (numbers.Number, bool)):
            TMS = bitarray(count*(bool(TMS),))
        if isinstance(TDI, (numbers.Number, bool)):
            TDI = bitarray(count*(bool(TDI),))
        #if isinstance(TDO, (numbers.Number, bool)):
        #    TDO = bitarray(count*(bool(TDO),))
        #    TDO = bitarray(count*('1' if TDO else '0'))
        if self._scanchain:
            self._scanchain._tap_transition_driver_trigger(TMS)
        #self.xpcu_single_read()
        outbits = bitarray()
        TMS.reverse()
        TDI.reverse()

        for bit_num in range(count):
            if TDO:
                b = self.xpcu_single_read()
                outbits.append(b)
            self.xpcu_single_write(TMS[bit_num], TDI[bit_num])

        if outbits:
            outbits.reverse()
            return outbits



    def xpcu_enable_output(self, enable):
        self._handle.controlWrite(0x40, 0xb0, 0x18 if enable else 0x10, 0, b'')

    def xpcu_enable_cpld_upgrade_mode(self, enable):
        self._handle.controlWrite(0x40, 0xb0, 0x52, 1 if enable else 0, b'')

    def xpcu_set_jtag_speed(self, speed_mode):
        self._handle.controlWrite(0x40, 0xb0, 0x28, 0x10|speed_mode, b'')

    def xpcu_get_GPIO_state(self):
        return ord(self._handle.controlRead(0xc0, 0xb0, 0x38, 0, 1))

    def xpcu_single_write(self, TMS, TDI):
        val = 0b100|(TMS<<1)|TDI
        self._handle.controlWrite(0x40, 0xb0, 0x30, val, b'')
        val = (TMS<<1)|TDI
        self._handle.controlWrite(0x40, 0xb0, 0x30, val, b'')

    def xpcu_single_read(self):
        b = self._handle.controlRead(0xC0, 0xb0, 0x38, 0, 1)
        return bool(ord(b)&1)

    def xpcu_GPIO_transfer(self, bit_count, data, *, bit_return_count=None):
        if bit_count < 1:
            raise ValueError()
        if bit_count > 0xFFFFFF+1:
            raise ValueError("Too many transactions. Max 16777216.")

        bit_count_dev = bit_count-1 #Controller uses 0 based bitcount.
        bit_count_low = bit_count_dev & 0xFFFF #16 bits for 'index' field
        bit_count_high = (bit_count_dev>>8) & 0xFF00

        if self._scanchain and self._scanchain._debug:
            print("***INPUT DATA TO CPXU (%s bits):"%(bit_count),
                  " ".join((hex(data)[2:].zfill(2)for data in data)))\
                  #pragma: no cover
        if bit_return_count is None:
            t = time()
            bit_return_count = XilinxPC1Driver._count_tdo_bits(data,
                                                               bit_count)
            if self._scanchain and self._scanchain._print_statistics:
                print("COUNT TDO BITS time        ", time()-t)\
                    #pragma: no cover

        self._handle.controlWrite(0x40, 0xb0, bit_count_high | 0xa6,
                                  bit_count_low, b'')

        t = time()
        bytec = self._handle.bulkWrite(2, data, timeout=120000)
        if self._scanchain and self._scanchain._print_statistics:
            print("TRANSFER time              ", time()-t)\
                #pragma: no cover

        if bit_return_count:
            t = time()
            bytes_wanted = int(math.ceil(bit_return_count/8.0))
            bytes_expected = bytes_wanted +(1 if bytes_wanted%2 else 0)
            ret = self._handle.bulkRead(6, bytes_expected, timeout=5000)

            if len(ret) != bytes_expected:
                raise Exception("Data returned is wrong lentgh. "
                                "Expected %s; Got %s. This is likely an "
                                "issue with the controller. Please report "
                                "The data you sent caused this error."
                                %(bytes_expected, len(ret)))

            if self._scanchain and self._scanchain._debug:
                print("OUTPUT DATA FROM XPCU (retbits: %s)"%
                      bit_return_count,
                      " ".join((hex(data)[2:].zfill(2)for data in ret)))\
                      #pragma: no cover

            raw_bits = XilinxPC1Driver._decode_tdo_bits(
                bytes(ret), bit_return_count=bit_return_count)

            assert len(raw_bits) == bit_return_count, \
                "WRONG BIT NUM CALCULATED; returned: %s; expected: %s"%\
                (len(raw_bits), bit_return_count)
            if self._scanchain and self._scanchain._print_statistics:
                print("RETURN DATA CALCULATION time", time()-t)\
                    #pragma: no cover
            return raw_bits

    def _get_speed(self):
        return self._set_speed(12000000)

    def _set_speed(self, speed):
        power = min(4,max(0,math.floor(math.log2(speed/750000))))
        self.xpcu_set_jtag_speed(4-power)
        return 750000 * (2**power)

    @staticmethod
    def _count_tdo_bits(data, bit_count):
        return bin(sum([((ord(data[i*2+1:i*2+2])>>4) &
                         (( 1<< min(4, bit_count-(i*4)) )-1) )<<4*i
                        for i in range(int(len(data)/2))])).count('1')

    @staticmethod
    def _decode_tdo_bits(ret, *, bit_return_count=None, bit_count=None):
        if bit_return_count is None:
            bit_return_count = XilinxPC1Driver._count_tdo_bits(ret,
                                                               bit_count)

        bytes_wanted = int(math.ceil(bit_return_count/8.0))
        bytes_expected = bytes_wanted +(1 if bytes_wanted%2 else 0)

        final_group_index = (bit_return_count-(bit_return_count%32))//8
        retiter = iter(ret[:final_group_index])
        fullgroups = [bytes(elem[::-1]) for elem in
                      zip(retiter, retiter, retiter, retiter)][::-1]
        other=ret[final_group_index:][::-1]
        other_bits = bitarray()
        other_bits.frombytes(other)
        other_bits = other_bits[:bit_return_count-(8*final_group_index)]

        reordered_data = b"".join(fullgroups)
        raw_bits = bitarray()
        raw_bits.frombytes(reordered_data)
        raw_bits = other_bits + raw_bits

        return raw_bits

__filter__ = [((0x03FD, 0x000D),XilinxPC1Driver),
              ((0x03FD, 0x0008),XilinxPC1Driver)]
