#!/usr/bin/env python
#Must be run from the project directory.

import time
from bitarray import bitarray
from flask import Flask, escape, render_template

from proteusisc.controllerManager import getDriverInstanceForDevice
from proteusisc.jtagScanChain import JTAGScanChain
from proteusisc.test_utils import FakeUSBDev, FakeDevHandle,\
    MockPhysicalJTAGDevice
from proteusisc.primitive import ConstantBitarray

ctrl = FakeDevHandle(MockPhysicalJTAGDevice(name="D0"),
                     MockPhysicalJTAGDevice(name="D1"),
                     MockPhysicalJTAGDevice(name="D2")
)
usbdev = FakeUSBDev(ctrl)
c = getDriverInstanceForDevice(usbdev)
print(c)
chain = JTAGScanChain(c)

devid = bitarray('11110110110101001100000010010011')
d0 = chain.initialize_device_from_id(chain, devid)
d1 = chain.initialize_device_from_id(chain, devid)
d2 = chain.initialize_device_from_id(chain, devid)
#d3 = chain.initialize_device_from_id(chain, devid)
chain._hasinit = True
chain._devices = [d0, d1, d2]#, d3]

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
    a, b, c, = None, None, None
    try:
        #chain.init_chain()
        #d0, d1, d2 = chain._devices
        chain.jtag_enable()
        #addprims()
        #a = chain.rw_dr(bitcount=32, read=True)
        #chain.transition_tap("TLR")
        #d0.rw_dev_dr(data=bitarray("1001"))
        #chain.rw_reg(data=bitarray('11001010'))
        #chain.sleep(delay=1)

        #chain.transition_tap("SHIFTIR");
        #chain.flush()
        #a = chain.rw_reg(data=ConstantBitarray(False, 8), read=True, lastbit=False)
        #b = chain.rw_reg(data=ConstantBitarray(False, 8), read=False, lastbit=False)
        #c = chain.rw_reg(data=ConstantBitarray(False, 8), read=True)
        #, bitcount=8)#7, lastbit=False)
        #chain.transition_tap("TLR");
        a = d0.rw_dev_ir(bitcount=8, read=True)
        #b = d1.rw_dev_ir(bitcount=8, read=True)
        c = d2.rw_dev_ir(bitcount=8, read=True)
        #a = d0.run_instruction("IDCODE", read=True,
        #                       data=bitarray('1100101000110101'*2))

        t = time.time()
        if not any((a, b, c)):
            print("NO PROMISES")
            chain.flush()
        if a:
            print("A", a(), a)
        if b:
            print("B", b(), b)
        if c:
            print("C", c(), c)
        print("\n\nSTUFF")
        print("TIME SPEND", time.time()-t)

    finally:
        chain.jtag_disable()
        print("DONE")
        print("\n\nDEV STATUS")
        for dev in ctrl.devices:
            print(dev.name)
            print("   ",dev.event_history)
        app.run(debug=False, use_reloader=False)
