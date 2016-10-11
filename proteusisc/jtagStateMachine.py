from .bittypes import bitarray

class JTAGStateMachine(object):
    """A software implementation of the JTAG TAP state machine.

    https://web.archive.org/web/20150923141837/http://www.embecosm.com/appnotes/ean5/images/tap-state-machine.png
    Instances of this class are used to track the state of JTAG
    devices, and calculate the operations required to get a chip
    in a specific state.

    This class is also used in JTAG Device simulators for testing.

    """
    states = {
        "_PRE5": ["_PRE5", "_PRE4"],
        "_PRE4": ["_PRE5", "_PRE3"],
        "_PRE3": ["_PRE5", "_PRE2"],
        "_PRE2": ["_PRE5", "_PRE1"],
        "_PRE1": ["_PRE5", "TLR"],
        "TLR": ["RTI", "TLR"],
        "RTI": ["RTI", "DRSCAN"],
        "DRSCAN": ["CAPTUREDR", "IRSCAN"],
        "CAPTUREDR": ["SHIFTDR","EXIT1DR"],
        "SHIFTDR": ["SHIFTDR","EXIT1DR"],
        "EXIT1DR": ["PAUSEDR","UPDATEDR"],
        "PAUSEDR": ["PAUSEDR","EXIT2DR"],
        "EXIT2DR": ["SHIFTDR","UPDATEDR"],
        "UPDATEDR": ["RTI","DRSCAN"],
        "IRSCAN": ["CAPTUREIR","TLR"],
        "CAPTUREIR": ["SHIFTIR","EXIT1IR"],
        "SHIFTIR": ["SHIFTIR","EXIT1IR"],
        "EXIT1IR": ["PAUSEIR","UPDATEIR"],
        "PAUSEIR": ["PAUSEIR","EXIT2IR"],
        "EXIT2IR": ["SHIFTIR","UPDATEIR"],
        "UPDATEIR": ["RTI","DRSCAN"]
        }

    def __init__(self, state=None):
        self.reset()
        if state:
            self.state = state


    def transition_bit(self, bit):
        choice = self.states.get(self._statestr, None)
        if choice is not None:
            self._statestr = choice[bit]

    @property
    def state(self):
        return self._statestr

    @state.setter
    def state(self, value):
        if value in self.states:
            self._statestr = value
        else:
            raise ValueError("%s is not a valid state for this state machine"%value)

    @classmethod
    def _find_shortest_path(cls, start, end, path=None):
        path = (path or []) + [start]
        if start == end:
            return path
        if start not in cls.states:
            return None # pragma: no cover
        shortest = None
        for node in cls.states[start]:
            if node not in path:
                newpath = cls._find_shortest_path(node, end, path)
                if newpath:
                    if not shortest or len(newpath) < len(shortest):
                        shortest = newpath
        return shortest

    @classmethod
    def _get_steps_from_nodes_path(cls, path):
        steps = []
        last_node = path[0]
        for node in path[1:]:
            steps.append(cls.states.get(last_node).index(node))
            last_node = node
        return bitarray(steps)

    _lookup_cache = {}
    def calc_transition_to_state(self, newstate):
        """Given a target state, generate the sequence of transitions that would move this state machine instance to that target state.

        Args:
            newstate: A str state name to calculate the path to.

        Returns:
            A bitarray containing the bits that would transition this
            state machine to the target state. The bits read from right
            to left. For efficiency, this retulting bitarray is cached.
            Do not edit this bitarray, or it will cause undefined
            behavior.
        """
        cached_val = JTAGStateMachine._lookup_cache.\
                     get((self.state, newstate))
        if cached_val:
            return cached_val

        if newstate not in self.states:
            raise ValueError("%s is not a valid state for this state "
                             "machine"%newstate)

        path = self._find_shortest_path(self._statestr, newstate)
        if not path:
            raise ValueError("No path to the requested state.")
        res = self._get_steps_from_nodes_path(path)
        res.reverse()
        JTAGStateMachine._lookup_cache[(self.state, newstate)] = res
        return res

    def reset(self):
        self._statestr = "_PRE5"

    def __repr__(self):
        return "<%s (State: %s)>"%\
            (self.__class__.__name__, self.state) # pragma: no cover

    def __eq__(self, other):
        if not isinstance(other, JTAGStateMachine):
            return NotImplemented
        return self.state == other.state
