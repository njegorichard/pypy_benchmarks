#!/usr/bin/env python
# -*- coding: utf-8 -*-
import util
import optparse
import time

import aes

cleartext = "This is a test. What could possibly go wrong? " * 2000 # 92000 bytes

def benchmark():
    moo = aes.AESModeOfOperation()
    cypherkey = [143,194,34,208,145,203,230,143,177,246,97,206,145,92,255,84]
    iv = [103,35,148,239,76,213,47,118,255,222,123,176,106,134,98,92]
    mode, orig_len, ciph = moo.encrypt(cleartext, moo.modeOfOperation["CBC"],
            cypherkey, moo.aes.keySize["SIZE_128"], iv)
    decr = moo.decrypt(ciph, orig_len, mode, cypherkey,
            moo.aes.keySize["SIZE_128"], iv)

    assert decr == cleartext

def main(arg):
    # XXX warmup

    times = []
    for i in xrange(arg):
        t0 = time.time()
        o = benchmark()
        tk = time.time()
        times.append(tk - t0)
        print tk - t0
    return times

if __name__ == "__main__":
    parser = optparse.OptionParser(
        usage="%prog [options]",
        description="Test the performance of the SlowAES cipher benchmark")
    util.add_standard_options_to(parser)
    options, args = parser.parse_args()

    util.run_benchmark(options, options.num_runs, main)
