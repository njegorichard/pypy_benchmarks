
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

TWISTED = [relative('lib/Twisted-9.0.0'), relative('lib/zope.interface-3.5.3/src')]

opts = {
    'gcbench' : {'iteration_scaling' : .10},
    'twisted_iteration': {'iteration_scaling': .10,
        'bm_env': {'PYTHONPATH': ':'.join(TWISTED)}},
    'twisted_web': {'iteration_scaling': .10,
        'bm_env': {'PYTHONPATH': ':'.join(TWISTED)}},
    'twisted_names': {'iteration_scaling': .10,
        'bm_env': {'PYTHONPATH': ':'.join(TWISTED)}},
}

for name in ['float', 'nbody_modified', 'meteor-contest', 'fannkuch',
             'spectral-norm', 'chaos', 'telco', 'gcbench',
             'twisted_iteration', 'twisted_web', 'twisted_names']:
    _register_new_bm(name, name, globals(), **opts.get(name, {}))
_register_new_bm('spitfire', 'spitfire', globals(),
    extra_args=['--benchmark=spitfire_o4'])
_register_new_bm('spitfire', 'spitfire_cstringio', globals(),
    extra_args=['--benchmark=python_cstringio'])

