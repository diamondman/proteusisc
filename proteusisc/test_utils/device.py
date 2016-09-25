from bitarray import bitarray
from collections import deque, Iterable

from ..jtagStateMachine import JTAGStateMachine

class ShiftRegister(object):
    """An emulator for a hardware shift register.

    https://en.wikipedia.org/wiki/Shift_register

    Many transfer protocols operate by sending data serially down a
    wire and into a fixed width shift register. After a number of bits
    has been received into the shift register, the data may be
    operated on as bytes, or whatever alignment the data has.  A shift
    register emulator is required to emulate hardware that receives
    data over a serial protocol, such as JTAG.

    Note that shifting data into a shift register by definition shift
    data out the other side of the register.

          |LEFT MOST BIT              RIGHT MOST BIT|
          __________________________________________
    IN => [][][][][][][][][][][][][][][][][][][][][] => OUT
          __________________________________________

    Attributes:
        size: An integer bitwidth of the register.
        initval: An boolean or bitarray to initialize the register's bits

    """

    def __init__(self, size, initval=False):
        self._size = size
        if isinstance(initval, Iterable):
            if size is not len(initval):
                raise ValueError("Mismatched size and length of initval")
            self._data = deque((b for b in initval), size)
        else:
            self._data = deque((initval for i in range(size)), size)

    @property
    def size(self):
        """Get the width of the shift register"""
        return self._size

    def __repr__(self):
        return "<ShiftRegister(%s)>"%self.size # pragma: no cover

    def shift(self, val):
        """Perform a single bitshift on the shift register

        Shifting a bit into the left of a shift register causes a bit
        to shift out of the right.

        Each shift on a shift register outputs the right most
        bit. Collecting these bits and adding them to an array will
        result in an array containing the reverse bit order as the
        register

             REG             SHIFT OUT ARRAY
             1100            []
        0 => 0110 => 0       [0]
        0 => 0011 => 0       [0, 0]
        0 => 0001 => 1       [0, 0, 1]
        0 => 0000 => 1       [0, 0, 1, 1]

        Args:
            val: A boolean value being shifted into the register.

        Returns:
            The boolean value shifted out of the right side of
            shift register.

        Usage:
            >>> from proteusisc.test_util import ShiftRegister
            >>> from bitarray import bitarray
            >>> sr = ShiftRegister(8, bitarray('11001010'))
            >>> ba = bitarray()
            >>> for i in range(8)
            ...     ba.append(sr.shift(False))
            >>> assert ba == bitarray('01010011')
        """
        res = self._data.pop()
        self._data.appendleft(val)
        #print("%s >> REG >> %s", (val, res))
        return res

    def clear(self, val=False):
        """Clear the shift register to a constant value.

        Args:
            val: A Boolean that all bits of the register will be set to.
        """
        self._data = deque((val for i in range(self.size)), self.size)

    def dumpData(self):
        """Reads out the data stored in the shift register

        Returns:
            A bitarray of all the data in the shiftregister.

            [True, False] => bitarray("10")
        """
        return bitarray(self._data)

class MockPhysicalJTAGDevice(object):
    def __init__(self, irlen=8, name=None, status=None, idcode=None):
        self.name = name
        self._custom_status = status
        self.event_history = []
        self.irlen = irlen
        self.IR = ShiftRegister(irlen)
        self._reg_BYPASS = ShiftRegister(1)
        self.DR = None
        self.tap = JTAGStateMachine()
        self.current_instruction = "IDCODE"

        self._idcode = idcode or \
                       bitarray('00000110110101001000000010010011')

        self._instruction_register_map = {
            'BULKPROG': 'DATAREG',
            'BYPASS': 'BYPASS',
            'ERASE_ALL': 'DATAREG',
            'EXTEST': 'BOUNDARY',
            'HIGHZ': 'BYPASS',
            'IDCODE': 'DEVICE_ID',
            'INTEST': 'BOUNDARY',
            'ISC_DISABLE': 'DATAREG',
            'ISC_ENABLE': 'DATAREG',
            'ISC_ENABLEOTF': 'DATAREG',
            'ISC_ENABLE_CLAMP': 'ISC_DEFAULT',
            'ISC_ERASE': 'DATAREG',
            'ISC_INIT': 'DATAREG',
            'ISC_NOOP': 'ISC_DEFAULT',
            'ISC_PROGRAM': 'DATAREG',
            'ISC_READ': 'DATAREG',
            'ISC_SRAM_READ': 'DATAREG',
            'ISC_SRAM_WRITE': 'DATAREG',
            'MVERIFY': 'DATAREG',
            'SAMPLE': 'BOUNDARY',
            'TEST_DISABLE': 'DATAREG',
            'TEST_ENABLE': 'DATAREG',
            'USERCODE': 'DEVICE_ID'}
        self._instructions = {
            'BULKPROG': '00010010',
            'BYPASS': '11111111',
            'ERASE_ALL': '00010100',
            'EXTEST': '00000000',
            'HIGHZ': '11111100',
            'IDCODE': '00000001',
            'INTEST': '00000010',
            'ISC_DISABLE': '11000000',
            'ISC_ENABLE': '11101000',
            'ISC_ENABLEOTF': '11100100',
            'ISC_ENABLE_CLAMP': '11101001',
            'ISC_ERASE': '11101101',
            'ISC_INIT': '11110000',
            'ISC_NOOP': '11100000',
            'ISC_PROGRAM': '11101010',
            'ISC_READ': '11101110',
            'ISC_SRAM_READ': '11100111',
            'ISC_SRAM_WRITE': '11100110',
            'MVERIFY': '00010011',
            'SAMPLE': '00000011',
            'TEST_DISABLE': '00010101',
            'TEST_ENABLE': '00010001',
            'USERCODE': '11111101'}
        self._registers_to_size = {
            'BOUNDARY': 552,
            'BYPASS': 1,
            'DATAREG': 1371,
            'DEVICE_ID': 32,
            'ISC_DEFAULT': 1}

        self.inscode_to_ins = {v:k for k,v in self._instructions.items()}

    @property
    def tapstate(self):
        return self.tap.state

    @property
    def idcode(self):
        return self._idcode.copy()

    def clearhistory(self):
        self.event_history = []

    def shift(self, tms, tdi):
        res = False
        #oldstate = self.tap.state
        if self.DR and self.tap.state=="SHIFTDR":
            res = self.DR.shift(tdi)
        if self.tap.state=="SHIFTIR":
            res = self.IR.shift(tdi)

        self.tap.transition_bit(tms)
        func = getattr(self, "_"+self.tap.state, None)
        if func:
            func()
        #print("%s State %s => %s; Reading %s"%
        #(self.name,oldstate,self.tap.state,res))
        return res

    def calc_status_register(self):
        data = self._custom_status if self._custom_status\
               else bitarray('11111011')
        return ShiftRegister(self.irlen, data)

    def _TLR(self):
        self.DR = ShiftRegister(32, self._idcode)
        self.event_history.append("RESET")
    def _RTI(self):
        self.event_history.append("RTI")
    def _CAPTUREDR(self):
        self.event_history.append("CAPTUREDR")

        if self.current_instruction == "IDCODE":
            self.DR = ShiftRegister(32, self._idcode)
        else:
            regname = self._instruction_register_map[
                self.current_instruction]
            reglen = self._registers_to_size[regname]
            self.DR = ShiftRegister(reglen)

    def _UPDATEDR(self):
        drval = self.DR.dumpData().to01()
        #print(self.name, "** Updated DR: %s"%(drval))
        self.event_history.append("UPDATEDR")
        self.event_history.append(drval)
    def _CAPTUREIR(self):
        self.event_history.append("CAPTUREIR")
        self.IR = self.calc_status_register()
    def _UPDATEIR(self):
        irval = self.IR.dumpData().to01()
        self.current_instruction = self.inscode_to_ins[irval]
        #print("** %s Updated IR: %s(%s); DR set to %s"%
        #      (self.name, irval, insname, regname))
        self.event_history.append("UPDATEIR")
        self.event_history.append(irval)
