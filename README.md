# ProteusISC

ProteusISC is a Linux JTAG controller abstraction library and driver framework. It is used for communicating to devices via JTAG using a JTAG controller.

[![License (LGPL version 2.1)](https://img.shields.io/badge/license-GNU%20LGPL%20version%202.1-blue.svg?style=flat-square)](http://opensource.org/licenses/LGPL-2.1)
[![CircleCI](https://circleci.com/gh/diamondman/proteusisc.svg?style=shield)](https://circleci.com/gh/diamondman/proteusisc)
[![codecov](https://codecov.io/gh/diamondman/proteusisc/branch/master/graph/badge.svg)](https://codecov.io/gh/diamondman/proteusisc)
[![Downloads](https://img.shields.io/pypi/diamondman/proteusisc.svg)](https://pypi.python.org/pypi/proteusisc)
[![Codacy Badge](https://api.codacy.com/project/badge/Grade/00c07105d4e44e96935875533c673288)](https://www.codacy.com/app/jessy-diamondman/proteusisc?utm_source=github.com&amp;utm_medium=referral&amp;utm_content=diamondman/proteusisc&amp;utm_campaign=Badge_Grade)
[![PyPI](https://img.shields.io/pypi/v/proteusisc.svg)](https://pypi.python.org/pypi/proteusisc/)
[![PyPI](https://img.shields.io/pypi/pyversions/proteusisc.svg)](https://pypi.python.org/pypi/proteusisc/)

The main benefits of proteusisc are:
* Use any supported JTAG Controller to talk to any JTAG Device, regardless of manufacturer.
* Agressive optimizations to commands sent to the JTAG Controller.
* Easy to use library for creating a new tool to configure a device type.
* Works in ipython for interactive JTAG exploration/debugging.

For more on the project, visit http://proteusisc.org/post/welcome/

To see hardware reverse engineering notes, visit http://diamondman.github.io/Adapt/.

For additional information on setting up supported jtag controllers, check the documentation link above.

## Installation / Setup from source

    pip3 install .

## Installation / Setup from pypi

    pip3 install proteusisc

## Testing

    pytest --cov-report term-missing --cov proteusisc -v

## Installation while developing

    pip install . -U --no-deps
