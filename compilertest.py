#!/usr/bin/env python
#Must be run from the project directory.

import time
from bitarray import bitarray
from flask import Flask, escape, render_template

from proteusisc.controllerManager import getDriverInstanceForDevice
from proteusisc.jtagScanChain import JTAGScanChain
from proteusisc.test_utils import FakeUSBDev, FakeDevHandle,\
    MockPhysicalJTAGDevice, FakeXPCU1Handle
from proteusisc.primitive import ConstantBitarray

#ctrl = FakeDevHandle(
ctrl = FakeXPCU1Handle(
    MockPhysicalJTAGDevice(name="D0", status=bitarray('11111100')),
#    MockPhysicalJTAGDevice(name="D1", status=bitarray('11111101')),
#    MockPhysicalJTAGDevice(name="D2", status=bitarray('11111110'))
)
usbdev = FakeUSBDev(ctrl)
c = getDriverInstanceForDevice(usbdev)
print(c)
chain = JTAGScanChain(c)

devid = bitarray('11110110110101001100000010010011')
d0 = chain.initialize_device_from_id(chain, devid)
#d1 = chain.initialize_device_from_id(chain, devid)
#d2 = chain.initialize_device_from_id(chain, devid)
#d3 = chain.initialize_device_from_id(chain, devid)
chain._hasinit = True
chain._devices = [d0]#, d1, d2]#, d3]

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
        #a, a_stat = d0.run_instruction("IDCODE", read=True)
        #assert a() == bitarray('00000110110101001000000010010011')
        #assert a_stat is None

        b, b_stat = d0.run_instruction("IDCODE", read_status=True)
        assert b is None
        assert b_stat() == bitarray('11111100')

        c, c_stat = d0.run_instruction("IDCODE", read=True, read_status=True)
        assert c() == bitarray('00000110110101001000000010010011')
        assert c_stat() == bitarray('11111100')


        t = time.time()
        if not any((a, b, c)) and len(chain._command_queue.queue):
            print("NO PROMISES")
            raise Exception()
            chain.flush()
        if a:
            print("A     ", a(), a)
        if a_stat:
            print("A_STAT", a_stat(), a_stat)
        if b:
            print("B     ", b(), b)
        if b_stat:
            print("A_STAT", b_stat(), b_stat)
        if c:
            print("C     ", c(), c)
        if c_stat:
            print("A_STAT", c_stat(), c_stat)
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
