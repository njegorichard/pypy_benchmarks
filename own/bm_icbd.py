import sys, os, subprocess, time
this_dir = os.path.abspath(os.path.dirname(__file__))

def main(n):
    # HAAAAAACK with subprocess because I can't get the thing
    # to run in-process :-(  As a result, it doesn't make
    # sense to run it more than once.

    d = os.environ.copy()
    d['PYTHONPATH'] = 'icbd'
    t0 = time.time()
    popen = subprocess.Popen(
                     [sys.executable,
                      '-m', 'icbd.type_analyzer.analyze_all',
                      '-I', 'stdlib/python2.5_tiny',
                      '-I', '.',
                      '-E', 'icbd/type_analyzer/tests',
                      '-E', 'icbd/compiler/benchmarks',
                      '-E', 'icbd/compiler/tests',
                      '-I', 'stdlib/type_mocks',
                      '-n',
                      'icbd'], cwd=this_dir, env=d, stdout=subprocess.PIPE)
    popen.communicate()
    time_elapsed = time.time() - t0
    return [time_elapsed] * n

if __name__ == "__main__":
    import util, optparse
    parser = optparse.OptionParser(
        usage="%prog [options]",
        description="Test the performance of the ICBD benchmark")
    util.add_standard_options_to(parser)
    options, args = parser.parse_args()

    util.run_benchmark(options, options.num_runs, main)
