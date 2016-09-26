# ProteusISC

ProteusISC is a Linux JTAG controller abstraction library and driver framework. It is used for communicating to devices via JTAG using a JTAG controller.

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