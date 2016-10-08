#-*- coding: utf-8 -*-
"""
    digilentdriver
    ~~~~~~~~~~~~~~

    Digilent driver for Linux USB JTAG controller

    :copyright: (c) 2014 by Jessy Diamond Exum
    :license: Pending, see LICENSE for more details.
"""

import math
import numbers

from proteusisc.cabledriver import CableDriver
from proteusisc.primitive import Level1Primitive,\
    Level2Primitive, Level3Primitive, Executable
from proteusisc.contracts import NOCARE, ZERO, ONE, CONSTANT, ARBITRARY
from proteusisc.errors import JTAGEnableFailedError,\
    JTAGAlreadyEnabledError, JTAGNotEnabledError
from proteusisc.bittypes import ConstantBitarray, CompositeBitarray,\
    Bitarray

#PROG = 8
#TCK = 4
#TMS = 2
#TDI = 1
#TDO = 1

class XPC1TransferPrimitive(Level1Primitive, Executable):
    #transfer_bits_single can be used for single bit jtag transfers.
    #This will be necessary for firmware upgrade.
    _function_name = 'transfer_bits'
    _driver_function_name = 'transfer_bits'#_single'#_cpld_upgrade'
    _max_bits = 65536
    _TMS, _TDI, _TDO = ARBITRARY, ARBITRARY, ARBITRARY
    def _get_args(self):
        if isinstance(self.tdo, CompositeBitarray):
            self.tdo = self.tdo.prepare(preserve_history=True)

        return [self.count], {"TMS":self.tms, "TDI":self.tdi,
                              'TDO': self.tdo}

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
        self._jtagon = False
        if self._dev.getProductID() == 0x0D:
            self._handle.releaseInterface(0)

        #self.xpcu_enable_cpld_upgrade_mode(False)

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
            TDO = ConstantBitarray(bool(TDO), count)
        if self._scanchain:
            self._scanchain._tap_transition_driver_trigger(TMS)

        bit_return_count = TDO.count(True)
        print("BIT RETURN COUNT", bit_return_count, len(TDO), count)

        from time import time
        t = time()
        outdata = bytearray(int(math.ceil(count/4.0))*2)
        tmsbytes = TMS.tobytes()
        tdibytes = TDI.tobytes()
        tdobytes = TDO.tobytes()

        adjusted_count = math.ceil(count/4)*4
        outbaseindex = 0
        inoffset = 0
        if count%8-4>0:
            #0xAa 0xBb 0xCc 0xDd = 0xab 0xcd
            outdata[0], outdata[1] = \
                ((tmsbytes[-1]<<4)&0xF0)|(tdibytes[-1]&0xF), \
                ((tdobytes[-1]<<4)&0xF0)|(0xF<<(4-(count%4)))&0xF
            outbaseindex = 2
        if count%8:
            #0xAa 0xBb 0xCc 0xDd = 0xAB 0xCD
            outdata[outbaseindex], outdata[outbaseindex+1] = \
                (tmsbytes[-1]&0xF0)|(tdibytes[-1]>>4), \
                (tdobytes[-1]&0xF0)|(0xFF<<(4-min(4, count%8)))&0xF
            outbaseindex += 2
            inoffset = 1

        readoffset = -(inoffset+1)
        # This is done this way because breaking these into variables
        # blows up the runtime. Thanks to mekarpeles for finding this.
        # Bit shifts and readoffset increased performance slightly.
        # Encoding 16777216 bits takes 3.2s, down from 80s (on 2.9 GHZ i7-3520M)
        for i in range(len(tmsbytes)-inoffset):#range(len(outdata)//4):
            outdata[(i<<2)+outbaseindex], outdata[(i<<2)+1+outbaseindex], \
                outdata[(i<<2)+2+outbaseindex], outdata[(i<<2)+3+outbaseindex] \
                = \
                ((tmsbytes[readoffset-i]&0x0F)<<4)|(tdibytes[readoffset-i]&0x0F), \
                ((tdobytes[readoffset-i]&0x0F)<<4)|0x0F,\
                (tmsbytes[readoffset-i]&0xF0)|(tdibytes[readoffset-i]>>4), \
                (tdobytes[readoffset-i]&0xF0)|0x0F


        print("XPCU1 byte blocks 2 Data Prepare Time:", time()-t)

        #print("LENGTH OF OUTDATA", len(outdata))
        return self.xpcu_GPIO_transfer(adjusted_count, outdata,
                    bit_return_count=bit_return_count)

    def transfer_bits_single(self, count, TMS, TDI, TDO=False):
        if not self._jtagon:
            raise JTAGNotEnabledError()
        if isinstance(TMS, (numbers.Number, bool)):
            TMS = Bitarray(count*('1' if TMS else '0'))
        if isinstance(TDI, (numbers.Number, bool)):
            TDI = Bitarray(count*('1' if TDI else '0'))
        #if isinstance(TDO, (numbers.Number, bool)):
        #    TDO = Bitarray(count*('1' if TDO else '0'))
        if self._scanchain:
            self._scanchain._tap_transition_driver_trigger(TMS)
        #self.xpcu_single_read()
        outbits = Bitarray()
        TMS.reverse()
        TDI.reverse()

        for bit_num in range(count):
            self.xpcu_single_write(TMS[bit_num], TDI[bit_num])
            if TDO:
                b = self.xpcu_single_read()
                outbits.append(b)

        if outbits:
            outbits.reverse()
            #print(outbits, len(outbits))
            return outbits

    def transfer_bits_single_cpld_upgrade(self, count, TMS, TDI, TDO=False):
        if not self._jtagon:
            raise JTAGNotEnabledError()
        if isinstance(TMS, (numbers.Number, bool)):
            TMS = Bitarray(count*('1' if TMS else '0'))
        if isinstance(TDI, (numbers.Number, bool)):
            TDI = Bitarray(count*('1' if TDI else '0'))
        #if isinstance(TDO, (numbers.Number, bool)):
        #    TDO = Bitarray(count*('1' if TDO else '0'))
        if self._scanchain:
            self._scanchain._tap_transition_driver_trigger(TMS)
        #self.xpcu_single_read()
        outbits = Bitarray()
        TMS.reverse()
        TDI.reverse()

        for bit_num in range(count):
            if TDO:
                b = self.xpcu_single_read()
                outbits.append(b)
            self.xpcu_single_write(TMS[bit_num], TDI[bit_num])

        if outbits:
            outbits.reverse()
            print(outbits, len(outbits))
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
        #print(bin(ord(b)))
        return bool(ord(b)&1)

    def xpcu_GPIO_transfer(self, bit_count, data, *, bit_return_count=None):
        if bit_count < 1:
            raise ValueError()
        if bit_count > 0xFFFFFF+1:
            raise ValueError("Too many transactions. Max 16777216.")

        bit_count_dev = bit_count-1 #Controller uses 0 based bitcount.
        bit_count_low = bit_count_dev & 0xFFFF #16 bits for 'index' field
        bit_count_high = (bit_count_dev>>8) & 0xFF00

        from time import time
        t = time()
        if self._scanchain and self._scanchain._debug:
            print("***INPUT DATA TO CPXU (%s bits):"%(bit_count),
                  " ".join((hex(data)[2:].zfill(2)for data in data)))
        if bit_return_count is None:
            bit_return_count = XilinxPC1Driver._count_tdo_bits(data,
                                                               bit_count)
        print("COUNT TDO BITS time        ", time()-t)

        #print("VALUE", hex(bit_count_high | 0xa6)[2:].zfill(4),
        #      "INDEX", hex(bit_count_low)[2:].zfill(4),
        #      "DATLEN", len(data))

        self._handle.controlWrite(0x40, 0xb0, bit_count_high | 0xa6,
                                  bit_count_low, b'')

        #print("DATA OUT", data)

        t = time()
        bytec = self._handle.bulkWrite(2, data, timeout=120000)
        print("TRANSFER time              ", time()-t)

        if bit_return_count:
            t = time()
            bytes_wanted = int(math.ceil(bit_return_count/8.0))
            bytes_expected = bytes_wanted +(1 if bytes_wanted%2 else 0)
            print("WANTED %s; EXPECTED %s"%(bytes_wanted, bytes_expected))
            ret = self._handle.bulkRead(6, bytes_expected, timeout=5000)

            if len(ret) != bytes_expected:
                raise Exception("Data returned is wrong lentgh. "
                                "Expected %s; Got %s. This is likely an "
                                "issue with the controller. Please report "
                                "The data you sent caused this error."
                                %(bytes_expected, len(ret)))

            #print(ret.hex())
            if self._scanchain and self._scanchain._debug:
                print("OUTPUT DATA FROM XPCU (retbits: %s)"%bit_return_count,
                      " ".join((hex(data)[2:].zfill(2)for data in ret)))

            raw_bits = XilinxPC1Driver._decode_tdo_bits(
                ret, bit_return_count=bit_return_count)

            assert len(raw_bits) == bit_return_count, \
                "WRONG BIT NUM CALCULATED; returned: %s; expected: %s"%\
                (len(raw_bits), bit_return_count)
            print("RETURN DATA CALCULATION time", time()-t)
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
            bit_return_count = XilinxPC1Driver._count_tdo_bits(data,
                                                               bit_count)

        bytes_wanted = int(math.ceil(bit_return_count/8.0))
        bytes_expected = bytes_wanted +(1 if bytes_wanted%2 else 0)

        final_group_index = (bit_return_count-(bit_return_count%32))//8
        retiter = iter(ret[:final_group_index])
        fullgroups = [bytes(elem[::-1]) for elem in
                      zip(retiter, retiter, retiter, retiter)][::-1]
        other=ret[final_group_index:][::-1]
        other_bits = Bitarray()
        other_bits.frombytes(other)
        other_bits = other_bits[:bit_return_count-(8*final_group_index)]

        reordered_data = b"".join(fullgroups)
        raw_bits = Bitarray()
        raw_bits.frombytes(reordered_data)
        raw_bits = other_bits + raw_bits

        return raw_bits

__filter__ = [((0x03FD, 0x000D),XilinxPC1Driver),
              ((0x03FD, 0x0008),XilinxPC1Driver)]
