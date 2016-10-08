# -*- coding: utf-8 -*-
"""
    adapt
    ~~~~~

    Linux USB JTAG controller for Digilent boards.

    :copyright: (c) 2014 by Jessy Diamond Exum.
    :license: Pending, see LICENSE for more details.
"""

__version__ = '0.1.0'

from .bittypes import Bitarray, ConstantBitarray, NoCareBitarray
from proteusisc.jtagScanChain import JTAGScanChain
from .controllerManager import getAttachedControllers
