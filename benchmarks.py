
import os
from unladen_swallow.perf import SimpleBenchmark, MeasureGeneric

def relative(*args):
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), *args)

def _register_new_bm(name, bm_name, d, **opts):
    def Measure(python, options):
        bm_path = relative('own', name + '.py')
        return MeasureGeneric(python, options, bm_path, **opts)
    Measure.func_name = 'Measure' + name.capitalize()

    def BM(*args, **kwds):
        return SimpleBenchmark(Measure, *args, **kwds)
    BM.func_name = 'BM_' + bm_name

    d[BM.func_name] = BM

opts = {
    'gcbench' : {'iteration_scaling' : .10},
}

for name in ['float', 'nbody_modified', 'meteor-contest', 'fannkuch',
             'spectral-norm', 'chaos', 'telco', 'gcbench']:
    _register_new_bm(name, name, globals(), **opts.get(name, {}))
_register_new_bm('spitfire', 'spitfire', globals(),
    extra_args=['--benchmark=spitfire_o4'])
_register_new_bm('spitfire', 'spitfire_cstringio', globals(),
    extra_args=['--benchmark=python_cstringio'])

