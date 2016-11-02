# -*- coding: utf-8 -*-
"""
    ProteusISC
    ~~~~~

    JTAG Controller Abstraction Library
    http://proteusisc.org/post/welcome/

    :copyright: (c) 2016 by Jessy Diamond Exum.
    :license: LGPL 2.1, see LICENSE for more details.
"""

__version__ = '0.2.0'

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
