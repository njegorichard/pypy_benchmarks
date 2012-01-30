#!/usr/bin/python
'''This is a dummy that does nothing except that it returns 1
second for every round of the benchmark.

You can use this as the baseline interpreter if you are only
interested in the time of the changed interpreter, but not
in the difference to a baseline interpreter.
'''
from own import util
import optparse

if __name__ == '__main__':
    parser = optparse.OptionParser(
        usage="%prog [options]",
        description="Test the performance of the Go benchmark")
    util.add_standard_options_to(parser)
    options, args = parser.parse_args()

    main = lambda n: [0.0001 for x in range(options.num_runs)]
    util.run_benchmark(options, options.num_runs, main)
