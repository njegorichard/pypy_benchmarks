
from rpython.annotator.annrpython import RPythonAnnotator
from rpython.translator.goal.targetrpystonedalone import pystones_main
from rpython.rtyper.rtyper import RPythonTyper

import time
l = []

for i in range(1):
    print i
    t0 = time.time()
    a = RPythonAnnotator()
    a.build_types(pystones_main, [int])
    rtyper = RPythonTyper(a)
    rtyper.specialize()
    l.append(time.time() - t0)

print l
