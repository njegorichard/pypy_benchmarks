import os
import logging
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
            if name == 'tcp':
                return 100*1024*1024/number
            elif name == 'iteration':
                return 10000/number
            else:
                return 100/number
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
    'bm_mako' : {'bm_env': {'PYTHONPATH': relative('lib/mako')}},
}

for name in ['float', 'nbody_modified', 'meteor-contest', 'fannkuch',
             'spectral-norm', 'chaos', 'telco', 'go', 'pyflate-fast',
             'raytrace-simple', 'crypto_pyaes', 'bm_mako']:
    _register_new_bm(name, name, globals(), **opts.get(name, {}))
for name in ['names', 'iteration', 'tcp', 'pb']:#, 'web', 'accepts']:
    iteration_scaling = 1.0
    _register_new_bm_twisted(name, 'twisted_' + name,
                     globals(), bm_env={'PYTHONPATH': ':'.join(TWISTED)},
                                 iteration_scaling=iteration_scaling)
_register_new_bm('spitfire', 'spitfire', globals(),
    extra_args=['--benchmark=spitfire_o4'])
_register_new_bm('spitfire', 'spitfire_cstringio', globals(),
    extra_args=['--benchmark=python_cstringio'])



# =========================================================================
# translate.py benchmark
# =========================================================================

def parse_timer(lines):
    prefix = '[Timer] '
    n = len(prefix)
    lines = [line[n:] for line in lines if line.startswith(prefix)]
    timings = []
    for line in lines:
        if (line == 'Timings:' or
            line.startswith('============') or
            line.startswith('Total:')):
            continue
        name, _, time = map(str.strip, line.partition('---'))
        name = name.replace('_lltype', '')
        name = name.replace('_c', '')
        name = name.replace('stackcheckinsertion', 'stackcheck')
        assert time.endswith(' s')
        time = float(time[:-2])
        timings.append((name, time))
    return timings

def test_parse_timer():
    lines = [
        'foobar',
        '....',
        '[Timer] Timings:',
        '[Timer] annotate                       --- 1.3 s',
        '[Timer] rtype_lltype                   --- 4.6 s',
        '[Timer] stackcheckinsertion_lltype     --- 2.3 s',
        '[Timer] database_c                     --- 0.4 s',
        '[Timer] ========================================',
        '[Timer] Total:                         --- 6.3 s',
        'hello world',
        '...',
        ]
    timings = parse_timer(lines)
    assert timings == [
        ('annotate', 1.3),
        ('rtype', 4.6),
        ('stackcheck', 2.3),
        ('database', 0.4)
        ]

def BM_translate(base_python, changed_python, options):
    """
    Run translate.py and returns a benchmark result for each of the phases.
    Note that we run it only with ``base_python`` (which corresponds to
    pypy-c-jit in the nightly benchmarks, we are not interested in
    ``changed_python`` (aka pypy-c-nojit) right now.
    """
    from unladen_swallow.perf import RawResult
    import subprocess

    translate_py = relative('lib/pypy/pypy/translator/goal/translate.py')
    #targetnop = relative('lib/pypy/pypy/translator/goal/targetnopstandalone.py')
    args = base_python + [translate_py, '--source', '--dont-write-c-files', '-O2']
    logging.info('Running %s', ' '.join(args))
    proc = subprocess.Popen(args, stderr=subprocess.PIPE)
    out, err = proc.communicate()
    retcode = proc.poll()
    if retcode != 0:
        print out
        print err
        raise Exception("translate.py failed")

    lines = err.splitlines()
    timings = parse_timer(lines)

    result = []
    for name, time in timings:
        data = RawResult([time], None)
        result.append((name, data))
    return result
BM_translate.benchmark_name = 'trans'
