
import os
from unladen_swallow.perf import SimpleBenchmark, MeasureGeneric

def MeasureFloat(python, options):
    bm_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                           'shootout', 'float.py')
    return MeasureGeneric(python, options, bm_path)

def BM_float(*args, **kwds):
    return SimpleBenchmark(MeasureFloat, *args, **kwds)
