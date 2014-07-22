# -*- coding: utf-8 -*-



import sys
import time, random
from common.abstract_threading import (
    atomic, Future, set_thread_pool, ThreadPool,
    hint_commit_soon, print_abort_info)

import itertools
from collections import deque


from sys import stdout
from math import sqrt, log


def chunks(iterable, size):
    it = iter(iterable)
    item = list(itertools.islice(it, size))
    while item:
        yield item
        item = list(itertools.islice(it, size))


def is_prime ( p ):
    if p == 2: return True # Lucas-Lehmer test only works on odd primes
    elif p <= 1 or p % 2 == 0: return False
    else:
        for i in range(3, int(sqrt(p))+1, 2 ):
            if p % i == 0: return False
    return True

def is_mersenne_prime ( p ):
    if p == 2:
        return True
    else:
        m_p = ( 1 << p ) - 1
        s = 4
        for i in range(3, p+1):
            s = (s ** 2 - 2) % m_p
        return s == 0


def work(ps, counter, upb_count):
    if counter[0] >= upb_count:
        return

    for p in ps:
        with atomic:
            if is_prime(p) and is_mersenne_prime(p):
                #print p
                counter[0] += 1
        if counter[0] >= upb_count:
            break


def run(threads=2, n=2000):
    threads = int(threads)
    n = int(n)

    set_thread_pool(ThreadPool(threads))


    precision = n   # maximum requested number of decimal places of 2 ** MP-1 #
    long_bits_width = precision * log(10, 2)
    upb_prime = int( long_bits_width - 1 ) / 2    # no unsigned #
    upb_count = 45      # find 45 mprimes if int was given enough bits #

    print " Finding Mersenne primes in M[2..%d]:" % upb_prime

    counter = [0]
    fs = []
    for ps in chunks(xrange(2, upb_prime+1), 500):
        fs.append(Future(work, ps, counter, upb_count))

    [f() for f in fs]
    print "found", counter[0]

    # shutdown current pool
    set_thread_pool(None)

    return



if __name__ == "__main__":
    run()
