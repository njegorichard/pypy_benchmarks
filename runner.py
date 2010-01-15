#!/usr/bin/env python
""" Usage: runner.py <result filename> <path to pypy-c>
"""

import os
import json
import sys
from unladen_swallow.perf import main

def run_and_store(benchmarks, result_filename, pypy_c_path):
    results = main(['-f', '-b', ','.join(benchmarks),
                    '--no_charts', sys.executable, pypy_c_path])
    f = open(str(result_filename), "w")
    f.write(json.dumps([(name, result.__class__.__name__, result.__dict__)
                    for name, result in results]))
    f.close()

if __name__ == '__main__':
    BENCHMARK_SET = ['richards', 'slowspitfire', 'django', 'spambayes',
                     'rietveld', 'html5lib', 'ai']
    run_and_store(BENCHMARK_SET, sys.argv[1], sys.argv[2])
