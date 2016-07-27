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

#Unknown if this should be kept around
class JTAGControlError(ProteusISCError):
    pass
