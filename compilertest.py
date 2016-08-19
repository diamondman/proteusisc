#!/usr/bin/env python
#Must be run from the project directory.

import time
from bitarray import bitarray
from flask import Flask, escape, render_template

from proteusisc.controllerManager import _controllerfilter
from proteusisc.jtagScanChain import JTAGScanChain
from proteusisc.test_utils import FakeDev

#drvr = _controllerfilter[0x03FD][0x0008]
drvr = _controllerfilter[0x1443][None]
c = drvr(FakeDev())
chain = JTAGScanChain(c)

devid = bitarray('11110110110101001100000010010011')
d0 = chain.initialize_device_from_id(chain, devid)
d1 = chain.initialize_device_from_id(chain, devid)
d2 = chain.initialize_device_from_id(chain, devid)
#d3 = chain.initialize_device_from_id(chain, devid)
chain._hasinit = True
chain._devices = [d0, d1, d2]#, d3]

a = d0.run_instruction("ISC_ENABLE", read=True, data=bitarray(bin(7)[2:].zfill(8)))
b = d0.run_instruction("ISC_ENABLE", read=False, execute=False, data=bitarray(bin(7)[2:].zfill(14)))#loop=8, delay=0.01)
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
#d0.rw_dev_dr(data=bitarray("1001"))
#d2.rw_dev_dr(data=bitarray("1001"))
#chain.rw_reg(data=bitarray('11001010'))
chain.sleep(delay=1)
chain.sleep(delay=2)
chain.sleep(delay=1)
chain.sleep(delay=2)
chain.sleep(delay=1)

app = Flask(__name__)

@app.route('/')
def report():
    t = time.time()
    stages = []
    stagenames = []

    chain._command_queue._compile(debug=True, stages=stages,
                                  stagenames=stagenames)

    print(time.time()-t)

    return render_template("layout.html", stages=stages,
                           stagenames=stagenames,
                           dev_count=len(chain._devices))

if __name__ == "__main__":
    app.run(debug=True)
