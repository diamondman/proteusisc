#!/usr/bin/env python
#Must be run from the project directory.

import time
from flask import Flask, escape, render_template

from proteusisc.controllerManager import getDriverInstanceForDevice
from proteusisc.jtagScanChain import JTAGScanChain
from proteusisc.test_utils import FakeUSBDev, FakeDevHandle,\
    MockPhysicalJTAGDevice, FakeXPCU1Handle
from proteusisc import ConstantBitarray, NoCareBitarray, bitarray

#ctrl = FakeDevHandle(
#ctrl = FakeXPCU1Handle(
#    MockPhysicalJTAGDevice(name="D0", status=bitarray('11111100')),
#    MockPhysicalJTAGDevice(name="D1", status=bitarray('11111101')),
#    MockPhysicalJTAGDevice(name="D2", status=bitarray('11111110'))
#
ctrl = FakeXPCU1Handle(
#ctrl = FakeDevHandle(
    MockPhysicalJTAGDevice(
        name="D0", status=bitarray('111100'),
        idcode=bitarray('00000001110000101110000010010011')),
    MockPhysicalJTAGDevice(
        name="D1", status=bitarray('111101'),
        idcode=bitarray('00000001110000101110000010010011')),
    MockPhysicalJTAGDevice(
        name="D2", status=bitarray('111110'),
        idcode=bitarray('00000001110000101110000010010011')),
)
usbdev = FakeUSBDev(ctrl)
c = getDriverInstanceForDevice(usbdev)
chain = JTAGScanChain(c, collect_compiler_artifacts=True)

#devid = bitarray('11110110110101001100000010010011')
devid = bitarray('00000001110000101110000010010011')
d0 = chain.initialize_device_from_id(chain, devid)
d1 = chain.initialize_device_from_id(chain, devid)
d2 = chain.initialize_device_from_id(chain, devid)
d3 = chain.initialize_device_from_id(chain, devid)
chain._hasinit = True
chain._devices = [d0, d1, d2]#, d3]

#import ipdb
#ipdb.set_trace()

app = Flask(__name__)

@app.route('/')
def report():
    if not chain._command_queue.stages:
        return "CHECK THAT FLUSH IS NOT DOUBLE CALLED"
    return render_template("layout.html",
                           stages=chain._command_queue.stages,
                           stagenames=chain._command_queue.stagenames,
                           dev_count=len(chain._devices))

if __name__ == "__main__":
    a, a_stat, b, b_stat, c, c_stat = [None]*6
    try:
        #chain.init_chain()
        #d0, d1, d2 = chain._devices
        chain.jtag_enable()
        #chain.transition_tap("SHIFTIR")


        #d0.run_instruction("CFG_IN", data=bitarray('11010001'))
        #d1.run_instruction("CFG_IN", data=bitarray('01101010111'))
        #d2.run_instruction("CFG_IN",data=bitarray('11110'))

        c, c_stat = d0.run_instruction("IDCODE", read=True)
        b, b_stat = d1.run_instruction("IDCODE", read=True)
        #c, c_stat = d0.run_instruction("CFG_IN",
        #                               data=bitarray('11010001'))
        #b, b_stat = d1.run_instruction("CFG_IN",
        #                               data=bitarray('01101010111'))
        #b, b_stat = d1.run_instruction("BYPASS", data=NoCareBitarray(1))
        #                               #data=bitarray('1'))
        #a, a_stat = d2.run_instruction("CFG_IN",
        #                               read=True, bitcount=8)
        #                               #data=bitarray('11110'))

        t = time.time()
        chain.flush()

        print()
        print("TIME SPENT", time.time()-t)
        for k in ('a', 'b', 'c'):
            if locals().get(k):
                print("%s     "%k, locals().get(k)())
            if locals().get(k+"_stat"):
                print("%s_STAT"%k, locals().get(k+"_stat")())

    finally:
        chain.jtag_disable()
        print("DONE\n")
        print("DEV STATUS")
        for dev in ctrl.devices:
            print(dev.name)
            print("   ",dev.event_history)
        app.run(debug=False, use_reloader=False)
