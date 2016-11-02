# -*- coding: utf-8 -*-
"""
    adapt
    ~~~~~

    Linux USB JTAG controller for Digilent boards.

    :copyright: (c) 2014 by Jessy Diamond Exum.
    :license: Pending, see LICENSE for more details.
"""

__version__ = '0.1.0'

from .bittypes import bitarray, ConstantBitarray, NoCareBitarray,\
    PreferFalseBitarray
from .jtagScanChain import JTAGScanChain
from .controllerManager import getAttachedControllers

def getInitializedChain(*args, cname=None, **kwargs):
    from .errors import NoMatchingControllerError,\
        ControllerFilterTooVagueError
    controllers = getAttachedControllers(cname)
    if len(controllers) == 0:
        raise NoMatchingControllerError()
    if len(controllers) > 1:
        raise ControllerFilterTooVagueError()
    c = controllers[0]

    chain = JTAGScanChain(c, *args, **kwargs)
    chain.init_chain()

    return chain
