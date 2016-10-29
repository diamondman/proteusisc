from collections import deque, Iterable

from ..bittypes import bitarray
from ..jtagStateMachine import JTAGStateMachine
from .. import jtagDeviceDescription

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
        self.loadData(initval)

    def __len__(self):
        """Get the width of the shift register"""
        return self._size

    def __repr__(self):
        return "<ShiftRegister(%s)>"%len(self) # pragma: no cover

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
        self._data = deque((val for i in range(len(self))), len(self))

    def dumpData(self):
        """Reads out the data stored in the shift register

        Returns:
            A bitarray of all the data in the shiftregister.

            [True, False] => bitarray("10")
        """
        return bitarray(self._data)

    def loadData(self, value):
        """Loads data into the shift register

        Args:
            An itarable (of the same length of the register) or a boolean to load into the shiftregister.
        """
        if isinstance(value, Iterable):
            if len(self) is not len(value):
                raise ValueError("Value not the length of the register.")
            self._data = deque((b for b in value), len(self))
        else:
            self._data = deque((value for i in range(len(self))),
                               len(self))

    def __bool__(self):
        return True

class BlackHoleShiftRegister(object):
    """An emulator for a hardware shift register that does not shift out.

    See the documentation for ShiftRegister.

    This class creates a similar shift register as ShiftReqister,
    except it automatically expands to hold everything shifted in, and
    never shifts data out. The data read from the output of the
    BlackHoleShiftRegister is undefined. Used to simulate JTAG
    Registers that do not connect their output to tdo, or otherwise
    violate the standard shift register properties of the JTAG chain
    (Such as Xilinx Spartan FPGAs that stream data into a register
    that has no defined length, where the chip processes the stream in
    real time, thus making shifting data out of the register
    meaningless).

    """

    def __init__(self):
        self.clear()

    def __len__(self):
        """Get the width of the shift register"""
        return len(self._data) #pragma: no cover

    def __repr__(self):
        return "<BlackHoleShiftRegister(%s)>"%self._data # pragma: no cover

    def shift(self, val):
        """Perform a single bitshift on the shift register

        In a normal ShiftRegister, Shifting a bit into the left of a
        shift register causes a bit to shift out of the right. But in
        a BlackHoleShiftRegister, the register expands to hold
        everything that is shifted into it, and bits read from the
        'output' are undefined.

        Returns:
            The boolean of undefined value

        """
        self._data.appendleft(val)
        return False

    def clear(self, val=False):
        """Clear the shift register to a constant value.

        Args:
            val: A Boolean that all bits of the register will be set to.
        """
        self._data = deque()

    def dumpData(self):
        """Reads out the data stored in the shift register

        Returns:
            A bitarray of all the data in the shiftregister.

            [True, False] => bitarray("10")
        """
        return bitarray(self._data)

    def __bool__(self):
        return True


class MockPhysicalJTAGDevice(object):
    def __init__(self, *, name=None, status=bitarray('11111011'),
                 idcode=bitarray('00000110110101001000000010010011'),
                 irlen=None, instructions=None, ins_reg_map=None,
                 registers=None):
        if any((instructions, ins_reg_map, registers, irlen)) and not\
           all((instructions, ins_reg_map, registers, irlen)):
            raise ValueError("Either initialize all reg/ins fields or "
                             "do not provide any.") #pragma: no cover
        self.name = name
        self._custom_status = status
        self._idcode = idcode
        self.tap = JTAGStateMachine()

        if all((instructions, ins_reg_map, registers, irlen)):
            self._instruction_register_map = ins_reg_map
            self._instructions = instructions
            self._registers = registers
            self._irlen = irlen
        else:
            numericid = int(self._idcode.to01(), 2)
            desc = jtagDeviceDescription.\
                   get_descriptor_for_idcode(numericid)
            self._instruction_register_map\
                = desc._instruction_register_map
            self._instructions = {k:v.to01() for k,v in
                                  desc._instructions.items()}
            self._registers = desc._registers
            self._irlen = desc._ir_length

        for ins in ("IDCODE", "BYPASS"):
            if ins not in self._instructions:
                raise ValueError("device instruction set must "
                                 "include %s"%ins)#pragma: no cover

        self.inscode_to_ins = {v:k for k,v in self._instructions.items()}

        self.event_history = []
        self.IR = ShiftRegister(self._irlen)
        self.DRs = {reg:ShiftRegister(l) for reg, l
                    in self._registers.items()}
        self.DRs[None] = BlackHoleShiftRegister()
        self.DRname = "DEVICE_ID"
        self.DR = self.DRs[self.DRname]
        self.current_instruction = "IDCODE"

    @property
    def tapstate(self):
        return self.tap.state

    @property
    def idcode(self):
        return self._idcode.copy()

    @property
    def irlen(self):
        return self._irlen

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

    def calc_status_register_val(self):
        #Meant to be overridden
        return self._custom_status

    def _TLR(self):
        self.DR = ShiftRegister(32, self._idcode)
        self.event_history.append("RESET")
    def _RTI(self):
        self.event_history.append("RTI")
    def _CAPTUREDR(self):
        self.event_history.append("CAPTUREDR")

        regname = self._instruction_register_map.get(
            self.current_instruction)
        self.DRname = regname
        self.DR = self.DRs[self.DRname]

        if self.current_instruction == "IDCODE":
            self.DR.loadData(self._idcode)
        if isinstance(self.DR, BlackHoleShiftRegister):
            self.DR.clear()

    def _UPDATEDR(self):
        drval = self.DR.dumpData().to01()
        #print(self.name, "** Updated DR: %s"%(drval))
        self.event_history.append("UPDATEDR")
        self.event_history.append(drval)
    def _CAPTUREIR(self):
        self.event_history.append("CAPTUREIR")
        self.IR.loadData(self.calc_status_register_val())
    def _UPDATEIR(self):
        irval = self.IR.dumpData().to01()
        self.current_instruction = self.inscode_to_ins[irval]
        #print("** %s Updated IR: %s(%s); DR set to %s"%
        #      (self.name, irval, insname, regname))
        self.event_history.append("UPDATEIR")
        self.event_history.append(irval)


class MockXC2C256(MockPhysicalJTAGDevice):
    def __init__(self):
        super(MockXC2C256, self).__init__(
            idcode=bitarray('00000110110101001000000010010011'),
            irlen=8,
            ins_reg_map={
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
                'USERCODE': 'DEVICE_ID'},
            instructions={
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
                'VERIFY': '00010011',
                'SAMPLE': '00000011',
                'TEST_DISABLE': '00010101',
                'TEST_ENABLE': '00010001',
                'USERCODE': '11111101'},
            registers={
                'BOUNDARY': 552,
                'BYPASS': 1,
                'DATAREG': 1371,
                'DEVICE_ID': 32,
                'ISC_DEFAULT': 1}
        )
