class ProteusISCError(Exception):
    pass


class JTAGEnableFailedError(ProteusISCError):
    pass

class JTAGAlreadyEnabledError(JTAGEnableFailedError):
    pass


class DevicePermissionDeniedError(ProteusISCError):
    pass


class JTAGNotEnabledError(ProteusISCError):
    pass

class JTAGTooManyDevicesError(ProteusISCError):
    pass

#Unknown if this should be kept around
class JTAGControlError(ProteusISCError):
    pass

class ProteusDataJoinError(ProteusISCError):
    def __init__(self, *args):
        super(ProteusDataJoinError, self).__init__(
            "Linkedlist pieces recombined not along seam.",
            *args
        )

class NoMatchingControllerError(ProteusISCError):
    pass

class ControllerFilterTooVagueError(ProteusISCError):
    pass
