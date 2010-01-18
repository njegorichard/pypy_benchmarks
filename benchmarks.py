
import os
from unladen_swallow.perf import SimpleBenchmark, MeasureGeneric

def relative(*args):
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), *args)

def _register_new_bm(name, d):
    def Measure(python, options):
        bm_path = relative('shootout', name + '.py')
        return MeasureGeneric(python, options, bm_path)
    Measure.func_name = 'Measure' + name.capitalize()

    def BM(*args, **kwds):
        return SimpleBenchmark(Measure, *args, **kwds)
    BM.func_name = 'BM_' + name

    d[BM.func_name] = BM

for name in ['float', 'nbody_modified', 'meteor-contest']:
    _register_new_bm(name, globals())
