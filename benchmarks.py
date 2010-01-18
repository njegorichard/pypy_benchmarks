
import py
from unladen_swallow.perf import SimpleBenchmark, MeasureGeneric

def MeasureFloat(python, options):
    bm_path = str(py.path.local(__file__).dirpath().join("shootout", "float.py"))
    return MeasureGeneric(python, options, bm_path)

def BM_float(*args, **kwds):
    return SimpleBenchmark(MeasureFloat, *args, **kwds)
