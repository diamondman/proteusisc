#!/usr/bin/env python
#Must be run from the project directory.

import time
from bitarray import bitarray
from flask import Flask, escape, render_template

from proteusisc.controllerManager import getDriverInstanceForDevice
from proteusisc.jtagScanChain import JTAGScanChain
from proteusisc.test_utils import FakeUSBDev, FakeDevHandle,\
    MockPhysicalJTAGDevice

ctrl = FakeDevHandle(MockPhysicalJTAGDevice(name="D0"),
                     MockPhysicalJTAGDevice(name="D1"),
                     MockPhysicalJTAGDevice(name="D2"))
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

def addprims():
    #d0.run_instruction("BYPASS", delay=0.01)
    a = d1.run_instruction("IDCODE", read=True, data=bitarray('1111111111111100'*2))#data=bitarray(bin(7)[2:].zfill(8)))
    a2 = d1.run_instruction("IDCODE", read=True, data=bitarray('1101010101010101'*2))#data=bitarray(bin(7)[2:].zfill(8)))
    b = d2.run_instruction("IDCODE", read=True, data=bitarray('0000000000000001'*2))#data=bitarray('11001010'*171+'111'))#loop=8, delay=0.01)
    b2 = d2.run_instruction("IDCODE", read=True, data=bitarray('1100101000110101'*2))#data=bitarray('11001010'*171+'111'))#loop=8, delay=0.01)
    #d0.rw_dev_ir(data=bitarray('11101000'))
    #for r in (bitarray(bin(i)[2:].zfill(8)) for i in range(2)):
    #    d0.run_instruction("ISC_PROGRAM", read=False, data=r, loop=8, delay=0.01)
    #d1.run_instruction("ISC_ENABLE", read=False, delay=0.01)
    #d1.run_instruction("ISC_ENABLE", read=False, execute=False, data=bitarray(), delay=0.01)
    #d1.run_instruction("ISC_ENABLE", read=False, loop=8, delay=0.01)
    #for r in (bitarray(bin(i)[2:].zfill(8)) for i in range(4,6)):
    #    d2.run_instruction("ISC_PROGRAM", read=False, data=r, loop=8, delay=.01)
    #d0.run_instruction("ISC_DISABLE", loop=8, delay=0.01)
    #d0.run_instruction("ISC_PROGRAM", read=False, data=bitarray(bin(7)[2:].zfill(8)), loop=8, delay=0.01)
    #chain.transition_tap("TLR")
    #chain.transition_tap("SHIFTIR")
    #chain.sleep(delay=1)
    #chain.rw_ir(data=bitarray('1001010'))
    #chain.rw_reg(data=bitarray('10'))
    #chain.transition_tap("RTI")

    #d0.rw_dev_dr(data=bitarray("1001"))
    #d2.rw_dev_dr(data=bitarray("1001"))
    #chain.rw_reg(data=bitarray('11001010'))
    #chain.sleep(delay=1)
    #chain.sleep(delay=2)
    #chain.sleep(delay=1)
    #chain.sleep(delay=2)
    #chain.sleep(delay=1)

app = Flask(__name__)

@app.route('/')
def report():
    #t = time.time()
    #stages = []
    #stagenames = []

    #chain._command_queue._compile(debug=True, stages=stages,
    #                              stagenames=stagenames)

    #print(time.time()-t)

    return render_template("layout.html",
                           stages=chain._command_queue.stages,
                           stagenames=chain._command_queue.stagenames,
                           dev_count=len(chain._devices))

if __name__ == "__main__":
    try:
        chain.jtag_enable()
        addprims()
        chain.flush()
        chain.jtag_disable()

    finally:
        #chain.jtag_disable()
        pass
    print("\n\nDEV STATUS")
    for dev in ctrl.devices:
        print(dev.name)
        print("   ",dev.event_history)
    print("DONE")

    app.run(debug=True, use_reloader=False)
