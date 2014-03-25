#!/usr/bin/python

import time
import math
import imp, os, sys
import json
import contextlib

def import_file(filepath):
    mod_name, file_ext = os.path.splitext(os.path.split(filepath)[-1])
    return imp.load_source(mod_name, filepath)


class DummyFile(object):
    def write(self, x): pass

@contextlib.contextmanager
def nostdout():
    save_stdout = sys.stdout
    sys.stdout = DummyFile()
    yield
    sys.stdout = save_stdout


def avg(xs):
    return sum(xs) / len(xs)

def std_dev(xs):
    N = len(xs)
    mu = avg(xs)
    var = sum([(x - mu)**2 for x in xs]) / N
    return math.sqrt(var)

def get_error(times):
    ts = sorted(times)[:args.k]
    best = float(ts[0])
    
    return max((t / best) - 1.0 for t in ts)

def within_error(args, times):
    return get_error(times) < args.error

def main(args):
    basedir = os.path.abspath(os.path.dirname(__file__))
    sys.path.insert(0, basedir+'/')
    import common
    print __file__
    folder = os.path.dirname(args.file)
    os.chdir(folder)
    sys.path.insert(0, os.path.abspath('.'))
    test = import_file(os.path.basename(args.file))

    times = []
    k = 1
    try:
        while True:
            time.sleep(0.2)
            if not args.q:
                print "Run {}/{}:".format(k, args.k)

            test_time = time.time()
            if args.p:
                test.run(*args.more)
            else:
                with nostdout():
                    test.run(*args.more)
            times.append(time.time() - test_time)

            if not args.q:
                print "took {} s".format(times[-1])

            if k >= args.k:
                if within_error(args, times):
                    break
                elif not args.q:
                    print "error was not within", args.error

                if k > 2 * args.k:
                    if not args.q:
                        print "max number of iterations reached", \
                            "error still too great, finish anyway"
                    break
            k += 1
    finally:
        if not args.q:
            print "times:", times

        if times:
            times = sorted(times)[:args.k]
            result = {'best':min(times),
                      'error':get_error(times),
                      'std_dev(k)':std_dev(times)}
            print json.dumps(result)



if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument('-k', default=3, help='K-best K', type=int)
    parser.add_argument('-e', '--error', default=0.05, type=float,
                        help='relative allowed error [0.05]')
    parser.add_argument('-q', action='store_const',
                        const=True, default=False,
                        help='mute except for best run')
    parser.add_argument('-p', action='store_const',
                        const=True, default=False,
                        help='print to stdout what the benchmark prints')
    parser.add_argument('file', help='file to run')
    parser.add_argument('more', nargs="*", help='file.run() arguments')

    args = parser.parse_args()
    if not args.q:
        print args
    main(args)
