#!/usr/bin/env python
""" Usage: runner.py <result filename> <path to pypy-c> <revnumber>
"""

import json
import socket
import sys

import benchmarks
from saveresults import save
from unladen_swallow import perf

BENCHMARK_SET = ['richards', 'slowspitfire', 'django', 'spambayes',
                 'rietveld', 'html5lib', 'ai']
BENCHMARK_SET += perf._FindAllBenchmarks(benchmarks.__dict__).keys()

# executeablenames
EX_CPY_PSYCO = "cpython psyco-profile"
EX_PYPY_C = 'pypy-c'
EX_PYPY_C_JIT = 'pypy-c-jit'


class WrongBenchmark(Exception):
    pass


def guess_executeable(pypy_c_path, postfix, args, changed):

    if ',' in args:
        args_baseline, args_changed = args.split(',')
        args = args_changed if changed else args_baseline

    if "psyco.sh" in pypy_c_path:
        executable_prefix = EX_CPY_PSYCO
    elif '--jit' in args:
        executable_prefix = EX_PYPY_C
    else:
        executable_prefix = EX_PYPY_C_JIT

    return executable_prefix + postfix


def run_and_store(benchmark_set, result_filename, pypy_c_path, revision=0,
                  options='', branch='default', args='', upload=False,
                  fast=False, baseline=sys.executable, full_store=False):
    funcs = perf.BENCH_FUNCS.copy()
    funcs.update(perf._FindAllBenchmarks(benchmarks.__dict__))
    opts = ['-b', ','.join(benchmark_set),
            '--inherit_env=PATH',
            '--no_charts']
    if fast:
        opts += ['--fast']
    if args:
        opts += ['--args', args]
    if full_store:
        opts += ['--no_statistics']
    opts += [baseline, pypy_c_path]
    results = perf.main(opts, funcs)
    f = open(str(result_filename), "w")
    results = [(name, result.__class__.__name__, result.__dict__)
           for name, result in results]
    f.write(json.dumps({
        'revision': revision,
        'results': results,
        'options': options,
        'branch': branch,
        }))
    f.close()
    return results


def main(argv):
    import optparse
    parser = optparse.OptionParser(
        usage="%prog [options]",
        description="Run benchmarks and dump json")
    parser.add_option("-b", "--benchmarks", metavar="BM_LIST",
                      default=','.join(BENCHMARK_SET),
                      help=("Comma-separated list of benchmarks to run"
                            " Valid benchmarks are: " +
                            ", ".join(sorted(BENCHMARK_SET))))
    parser.add_option('-p', '--pypy-c', default=sys.executable,
                      help='pypy-c or other modified python to run against')
    parser.add_option('-r', '--revision', default=0, action="store",
                      help='specify revision of pypy-c')
    parser.add_option('-o', '--output-filename', default="result.json",
                      action="store",
                      help='specify output filename to store resulting json')
    parser.add_option('--options', default='', action='store',
                      help='a string describing picked options, no spaces')
    parser.add_option('--branch', default='default', action='store',
                      help="pypy's branch")
    parser.add_option('--baseline', default=sys.executable, action='store',
                      help='baseline interpreter, defaults to host one')
    parser.add_option("-a", "--args", default="",
                      help=("Pass extra arguments to the python binaries."
                            " If there is a comma in this option's value, the"
                            " arguments before the comma (interpreted as a"
                            " space-separated list) are passed to the baseline"
                            " python, and the arguments after are passed to"
                            " the changed python. If there's no comma, the"
                            " same options are passed to both."))
    parser.add_option("--upload", default=None, action="store_true",
                      help=("Upload results to speed.pypy.org (unless "
                            "--upload-url is given)."))
    parser.add_option("--upload-urls", default="http://speed.pypy.org/",
                      help=("Comma seperated urls of the codespeed instance to"
                            " upload to (default: http://speed.pypy.org/)."))
    parser.add_option("--upload-project", default="PyPy",
                      help="The project name in codespeed (default: PyPy).")
    parser.add_option("--upload-executable", default=None,
                      help=("The executable name in codespeed "
                            "(guessed if possible and not given)."))
    parser.add_option("--force-host", default=None, action="store",
                      help="Force the hostname")
    parser.add_option("--fast", default=False, action="store_true",
                      help="Run shorter benchmark runs")
    parser.add_option("--full-store", default=False, action="store_true",
                      help="")
    parser.add_option('--postfix', default='', action='store',
                      help='Append a postfix to uploaded executable')
    options, args = parser.parse_args(argv)
    #
    # use 'default' if the branch is empty
    if not options.branch:
        options.branch = 'default'

    benchmarks = options.benchmarks.split(',')
    for benchmark in benchmarks:
        if benchmark not in BENCHMARK_SET:
            raise WrongBenchmark(benchmark)

    pypy_c_path = options.pypy_c
    baseline = options.baseline
    fast = options.fast
    args = options.args
    full_store = options.full_store
    output_filename = options.output_filename

    project = options.upload_project
    executable = options.upload_executable
    postfix = options.postfix
    branch = options.branch
    revision = options.revision

    force_host = options.force_host

    results = run_and_store(benchmarks, output_filename, pypy_c_path, revision,
                            args=args, fast=fast, baseline=baseline,
                            full_store=full_store, branch=branch)

    if options.upload:
        changed = 'pypy' not in baseline
        if executable is None:
            executable = guess_executeable(pypy_c_path, postfix, args, changed)

        if executable == EX_CPY_PSYCO:
            revision = 100
            project = 'cpython'

        changed = False

        host = force_host if force_host else socket.gethostname()
        for url in options.upload_urls.split(','):
            print save(project, revision, results, executable, host, url,
                       changed=changed, branch=branch)


if __name__ == '__main__':
    main(sys.argv[1:])
