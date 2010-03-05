
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

def _register_new_bm_twisted(name, bm_name, d, **opts):
    def Measure(python, options):
        def parser(line):
            number = float(line.split(" ")[0])
            return 3000/number
        bm_path = relative('own', 'twisted', name + '.py')
        return MeasureGeneric(python, options, bm_path, parser=parser, **opts)
    Measure.func_name = 'Measure' + name.capitalize()

    def BM(*args, **kwds):
        return SimpleBenchmark(Measure, *args, **kwds)
    BM.func_name = 'BM_' + bm_name

    d[BM.func_name] = BM

TWISTED = [relative('lib/twisted-trunk'), relative('lib/zope.interface-3.5.3/src'), relative('own/twisted')]

opts = {
    'gcbench' : {'iteration_scaling' : .10},
}

for name in ['float', 'nbody_modified', 'meteor-contest', 'fannkuch',
             'spectral-norm', 'chaos', 'telco']:
    _register_new_bm(name, name, globals(), **opts.get(name, {}))
for name in ['web', 'names', 'accepts', 'iteration', 'tcp', 'pb']:
    if name == 'accepts':
        iteration_scaling = .07
    elif name == 'web':
        iteration_scaling = .12
    else:
        iteration_scaling = .20
    _register_new_bm_twisted(name, 'twisted_' + name,
                     globals(), bm_env={'PYTHONPATH': ':'.join(TWISTED)},
                                 iteration_scaling=iteration_scaling)
_register_new_bm('spitfire', 'spitfire', globals(),
    extra_args=['--benchmark=spitfire_o4'])
_register_new_bm('spitfire', 'spitfire_cstringio', globals(),
    extra_args=['--benchmark=python_cstringio'])

