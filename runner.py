#!/usr/bin/env python
""" Usage: runner.py <result filename> <path to pypy-c> <revnumber>
"""

import os
import json
import sys
from unladen_swallow.perf import main, BENCH_FUNCS, _FindAllBenchmarks
import benchmarks

def run_and_store(benchmark_set, result_filename, pypy_c_path, revision=0):
    funcs = BENCH_FUNCS.copy()
    funcs.update(_FindAllBenchmarks(benchmarks.__dict__))
    results = main(['-f', '-b', ','.join(benchmark_set),
                    '--inherit_env=PATH',
                    '--no_charts', sys.executable, pypy_c_path],
                   funcs)
    f = open(str(result_filename), "w")
    res = [(name, result.__class__.__name__, result.__dict__)
           for name, result in results]
    f.write(json.dumps({
        'revision' : revision,
        'results' : res,
        }))
    f.close()

if __name__ == '__main__':
    BENCHMARK_SET = ['richards', 'slowspitfire', 'django', 'spambayes',
                     'rietveld', 'html5lib', 'ai', 'float']
    run_and_store(BENCHMARK_SET, sys.argv[1], sys.argv[2], int(sys.argv[3]))
