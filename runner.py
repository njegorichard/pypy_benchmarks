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

CHANGED = 'changed'
BASELINE = 'baseline'


class WrongBenchmark(Exception):
    pass


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


def get_upload_options(options):
    '''
    returns a dict with 2 keys: CHANGED, BASELINE. The values are
    dicts with the keys
    * 'upload' (boolean)
    * 'project' (string)
    * 'executable' (string)
    * 'urls (list of strings).
    * 'branch' (string)
    * 'revision' (string)

    This correspondents to the the --upload* and --upload-baseline*
    options.

    raises: AssertionError if upload is specified, but not the
    corresponding executable or revision.
    '''

    if options.upload_baseline_revision is None:
        options.upload_baseline_revision = options.upload_revision

    upload_options = {}

    for run in [CHANGED, BASELINE]:

        def get_upload_option(name):
            attr_name = 'upload'
            if run == BASELINE:
                attr_name = '%s_baseline' % attr_name
            if name:
                attr_name = '%s_%s' % (attr_name, name)
            return getattr(options, attr_name)

        urls = get_upload_option('urls')
        urls = [url.strip() for url in urls.split(',') if url.strip()]
        upload = get_upload_option(None)
        project = get_upload_option('project')
        executable = get_upload_option('executable')
        branch = get_upload_option('branch')
        revision = get_upload_option('revision')
        if upload:
            if executable is None:
                raise AssertionError('If you want to --upload[-baseline] you '
                                     'have to specify the corresponding '
                                     '--upload[-baseline]-executable')
            if revision is None:
                raise AssertionError('If you want to upload the result you '
                                     'have to specify a --revision (or '
                                     '--upload-baseline-revision if you '
                                     'want to upload the baseline result')
            if ((run == BASELINE and 'nullpython.py' in options.baseline) or
                (run == CHANGED and 'nullpython.py' in options.pypy_c)):
                raise AssertionError("Don't upload data from the nullpython "
                                     "dummy interpreter. It won't run any "
                                     "real benchmarks.")

        upload_options[run] = {
            'upload': upload,
            'project': project,
            'executable': executable,
            'urls': urls,
            'branch': branch,
            'revision': revision}
    return upload_options


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
    parser.add_option('-r', '--revision', action="store",
                      dest='upload_revision',
                      help='specify revision of pypy-c')
    parser.add_option('-o', '--output-filename', default="result.json",
                      action="store",
                      help='specify output filename to store resulting json')
    parser.add_option('--options', default='', action='store',
                      help='a string describing picked options, no spaces')
    parser.add_option('--branch', default='default', action='store',
                      dest='upload_branch',
                      help="pypy's branch (default: 'default'")
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
                      help=("Comma seperated urls of the codespeed instances "
                            "to upload to (default: http://speed.pypy.org/)."))
    parser.add_option("--upload-project", default="PyPy",
                      help="The project name in codespeed (default: PyPy).")
    parser.add_option("--upload-executable", default=None,
                      help="The executable name in codespeed.")
    parser.add_option("--upload-baseline", default=None, action="store_true",
                      help=("Also upload results or the baseline benchmark "
                            "to speed.pypy.org (unless "
                            "--upload-baseline-url is given)."))
    parser.add_option("--upload-baseline-urls",
                      default="http://speed.pypy.org/",
                      help=("Comma seperated urls of the codespeed instances "
                            "to upload to (default: http://speed.pypy.org/)."))
    parser.add_option("--upload-baseline-project", default="PyPy",
                      help="The project name in codespeed (default: PyPy).")
    parser.add_option("--upload-baseline-executable", default=None,
                      help="The executable name in codespeed.")
    parser.add_option('--upload-baseline-branch', default='default',
                      action='store',
                      help=("The name of the branch used for the baseline "
                            "run. (default: 'default'"))
    parser.add_option('--upload-baseline-revision', action='store',
                      default=None,
                      help=("The revision of the baseline "
                            "run. (default: the revision given with -r"))

    parser.add_option("--force-host", default=None, action="store",
                      help="Force the hostname")
    parser.add_option("--fast", default=False, action="store_true",
                      help="Run shorter benchmark runs")
    parser.add_option("--full-store", default=False, action="store_true",
                      help="")

    options, args = parser.parse_args(argv)

    upload_options = get_upload_options(options)
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

    branch = options.upload_branch
    revision = options.upload_revision
    force_host = options.force_host

    results = run_and_store(benchmarks, output_filename, pypy_c_path, revision,
                            args=args, fast=fast, baseline=baseline,
                            full_store=full_store, branch=branch)

    for run in [CHANGED, BASELINE]:
        upload = upload_options[run]['upload']
        urls = upload_options[run]['urls']
        project = upload_options[run]['project']
        executable = upload_options[run]['executable']
        branch = upload_options[run]['branch']
        revision = upload_options[run]['revision']

        if upload:
            # prevent to upload results from the nullpython dummy
            host = force_host if force_host else socket.gethostname()
            for url in urls:
                print save(project, revision, results, executable, host, url,
                           changed=(run == CHANGED), branch=branch)


if __name__ == '__main__':
    main(sys.argv[1:])
