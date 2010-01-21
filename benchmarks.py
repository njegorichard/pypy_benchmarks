
import os
from unladen_swallow.perf import SimpleBenchmark, MeasureGeneric

def relative(*args):
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), *args)

def _register_new_bm(name, d, **opts):
    def Measure(python, options):
        bm_path = relative('own', name + '.py')
        return MeasureGeneric(python, options, bm_path, **opts)
    Measure.func_name = 'Measure' + name.capitalize()

    def BM(*args, **kwds):
        return SimpleBenchmark(Measure, *args, **kwds)
    BM.func_name = 'BM_' + name

    d[BM.func_name] = BM

opts = {
    'gcbench' : {'iteration_scaling' : .10},
}

for name in ['float', 'nbody_modified', 'meteor-contest', 'fannkuch',
             'spectral-norm', 'chaos', 'telco', 'gcbench']:
    _register_new_bm(name, globals(), **opts.get(name, {}))
