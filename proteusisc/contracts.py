class Requirement(object):
    """Electrical requirement of a signal, or a controller message's capabilitys/limitations to control a signal.

    Represents the ability of a ISC Controller to transmit data on a
    signal (wire). A LV1 primitives have different levels of
    expressiveness per signal.  For each signal, a primitive be able
    tos end one of the following 4 values during the primitive's
    execution:

        Only 0 (Primitive always sets signal to 0)
        Only 1 (Primitive always sets signal to 1)
        Either 0 OR 1 (Constant for the full primitive execution)
        Any arbitrary sequence of 0 and 1.

    This class is wrapping a 4 bit number:
    ABCD
    1XXX = ARBITRARY (A)
    000X = NOCARE (-)
    0010 = ZERO (0)
    0011 = ONE (1)
    01X0 = (CONSTANT) ZERO. use ZERO (C0)
    01X1 = (CONSTANT) ONE. use ONE (C1)

    A Requirement instance can behave in two ways:
        Describe the capability of a primitive with respect to a signal:
            Constant specifies that the primitive can send either 0 or 1
            to the respective signal.
        Describe matching requirements for expanding primitives
            Constant is treated the same as single since it is just the
            requirement of an existing primitive.

    """
    def __init__(self, arbitrary, constant, single, value):
        self.arbitrary = arbitrary
        self.constant = constant
        self.single = single
        self.value = value

    def copy(self):
        return Requirement(self.arbitrary, self.constant, self.single,
                           self.value)

    @property
    def A(self):
        "Bitname for 'Arbitrary' in original equation derivation."
        return self.arbitrary
    @property
    def B(self):
        "Bitname for 'Constant' in original equation derivation."
        return self.constant
    @property
    def C(self):
        "Bitname for 'Single' in original equation derivation."
        return self.single
    @property
    def D(self):
        "Bitname for 'Value' in original equation derivation."
        return self.value
    @property
    def isnocare(self):
        """Checks if this requirement has no preference.

        The bits in a requirement have a precedence:
            Arbitrary>Constant>Single

        Value only matters for if the set bit with the highest
        precedence is Constant or Single.

        A Requirement is NoCare when none of the precedence bits are
        set. The Value bit does not effect this calculation.

        """
        return not self.arbitrary and not self.constant \
            and not self.single
    @property
    def isarbitrary(self):
        """Checks the 'arbitrary' attribute by precedence.

        Can mean two things based on how this Requirement is being used:
        As a Data Requirement:
            Does this requirement specify the need to control the
            value asserted to a data line for every clock cycle

        As a Capability:
            Does this Capability guarantee the ability to assert an
            arbitrary value to a data line for eachclock cycles.

        """
        return self.arbitrary
    @property
    def isconstant(self):
        """Checks the 'constant' attribute by precedence.

        Can mean two things based on how this Requirement is being used:
        As a Data Requirement:
            Does this requirement specify the need for a constant
            value to be asserted to a data line for 1 or more clock
            cycles

        As a Capability:
            Does this Capability guarantee the ability to assert a
            constant (configurable) value to a data line for one or
            more clock cycles, no more and no less.
        """
        return not self.arbitrary and self.constant
    @property
    def issingle(self):
        """Checks the 'single' attribute by precedence.

        Not used by requirements, only needed when the Requirement is
        used as a capability.

        True if the capability allows asserting a single value (0 or 1
        not configurable) to a data line for one or more clock
        cycles. Similar to 'constant' but represents EITHER the
        ability to assert a 1 OR an ability to assert a 0, not the
        ability to configure which.

        """
        return not self.arbitrary and not self.constant and self.single

    def satisfies(self, other):
        """Check if the capabilities of a primitive are enough to satisfy a requirement.

        Should be called on a Requirement that is acting as a
        capability of a primitive. This method returning true means
        that the capability advertised here is enough to handle
        representing the data described by the Requirement passed in
        as 'other'.

        Here is a chart showing what satisfies what.

             other
              A C 0 1
           |Y N N N N
        s A|Y Y Y Y Y
        e C|Y - Y Y Y
        l 0|Y * * Y N
        f 1|Y * * N Y

        ' ' = No Care
        A = arbitrary
        C = Constant
        0 = ZERO
        1 = ONE

        Y = YES
        N = NO
        - = Could satisfy with multiple instances
        * = Not yet determined behavior. Used for bitbanging controllers.

        """
        if other.isnocare:
            return True
        if self.isnocare:
            return False
        if self.arbitrary:
            return True
        if self.constant and not other.arbitrary:
            return True
        if self.value is other.value and not other.arbitrary\
           and not other.constant:
            return True
        return False

    @property
    def score(self):
        return sum([v<<i for i, v in
                    enumerate(reversed(
                        (self.A, self.B, self.C))
                    )])

    def __repr__(self):
        """Return a character code and bit states of the Requirement.

        Character code is:
            A for Arbitrary
            C for Constant
            F for False Single
            T for True Single
            - for NoCare

        The bits are Arbitrary, Constant, Single, and Value in that order.
        """
        if self.arbitrary:
            l = 'A'
        elif self.constant:
            l = "C"
        elif self.single:
            l = "T" if self.value else "F"
        else:
            l = "-"
        return l+"("+bin(sum([v<<i for i, v in
                        enumerate(reversed(
                            (self.A, self.B, self.C, self.D))
                        )]))[2:].zfill(4) +")"

    def __add__(self, other):
        """Combines two Requirements.

        Assumes both Requirements are being used as feature requests.
        Adding two Requirements being used as feature lists for a
        primitive has no meaning.

        The following code is a reduced K-map of the full interaction
        of two Requirement objects. For details, see
        requirements_description.txt in the documentation.
        """
        if not isinstance(other, Requirement):
            return NotImplemented
        a1, a2, a3, a4, b1, b2, b3, b4 = self.A, self.B, self.C, self.D, other.A, other.B, other.C, other.D
        A = (a1 or a2 or a3 or b1)and(a1 or a4 or b1 or b4)and(a1 or b1 or b2 or b3)and(a1 or not a4 or b1 or not b4)
        B = False
        C = b3 or b2 or a3 or a2
        D = (a2 or a3 or b4)and(a4 or b2 or b3)and(a4 or b4)
        res = Requirement(A, B, C, D)
        #print(self, a1, a2, a3, a4)
        #print(other, b1, b2, b3, b4)
        #print(res, A, B, C, D, "\n")
        return res

NOCARE =       Requirement(False, False, False, False)
ZERO =         Requirement(False, False, True,  False)
ONE =          Requirement(False, False, True,  True)
CONSTANT    =  Requirement(False, True,  False, False)
CONSTANTZERO = Requirement(False, True,  False, False)
CONSTANTONE =  Requirement(False, True,  False, True)
ARBITRARY =    Requirement(True,  False, False, False)
