
from subprocess import Popen, PIPE
import os
import time

def main(n):
    d = os.path.dirname
    directory = os.path.join(d(d(os.path.abspath(__file__))), 'lib', 'waf', 'build')
    times = []
    for i in range(n):
        t0 = time.time()
        Popen(['./waf', 'configure'], cwd=directory,
              stdout=PIPE, stderr=PIPE).communicate()
        Popen(['./waf', 'clean', 'build', '-j3', '-p'],
              cwd=directory, stdout=PIPE, stderr=PIPE).communicate()
        times.append(time.time() - t0)
    return times

if __name__ == "__main__":
    import util, optparse
    parser = optparse.OptionParser(
        usage="%prog [options]",
        description="Test the performance of the Waf benchmark")
    util.add_standard_options_to(parser)
    options, args = parser.parse_args()
    util.run_benchmark(options, options.num_runs, main)
