# -*- coding: utf-8 -*-



import sys
import time, random
from common.abstract_threading import (
    atomic, Future, set_thread_pool, ThreadPool,
    hint_commit_soon, print_abort_info)

import itertools
from collections import deque


def chunks(iterable, size):
    it = iter(iterable)
    item = list(itertools.islice(it, size))
    while item:
        yield item
        item = list(itertools.islice(it, size))



def qsort(xs, l0, n):
    if n < 2:
        return
    pivot = xs[l0 + n // 2]
    l = l0
    r = l + n - 1
    while l <= r:
        if xs[l] < pivot:
            l += 1
            continue
        if xs[r] > pivot:
            r -= 1
            continue
        xs[l], xs[r] = xs[r], xs[l]
        l += 1
        r -= 1
    qsort(xs, l0, r - l0 + 1)
    qsort(xs, l, l0 + n - l)



def qsort_f(xs, l0, n, level):
    if n < 2:
        return []

    pivot = xs[l0 + n // 2]
    l = l0
    r = l + n - 1
    while l <= r:
        with atomic:
            xl = xs[l]
            if xl < pivot:
                l += 1
                continue
            xr = xs[r]
            if xr > pivot:
                r -= 1
                continue
            xs[l], xs[r] = xr, xl
            l += 1
            r -= 1

    fs = []
    # only start futures on a single level:
    do_futures = level == 4
    largs = (xs, l0, r - l0 + 1, level+1)
    rargs = (xs, l, l0 + n - l, level+1)
    leftf, rightf = False, False

    if do_futures:
        if largs[2] > 2000:
            fs.append(Future(qsort_f, *largs))
            leftf = True

        if rargs[2] > 2000:
            fs.append(Future(qsort_f, *rargs))
            rightf = True

    if not leftf:
        if level >= 4 and largs[2] < 500:
            with atomic:
                fs.extend(qsort_f(*largs))
        else:
            fs.extend(qsort_f(*largs))

    if not rightf:
        if level >= 4 and rargs[2] < 500:
            with atomic:
                fs.extend(qsort_f(*rargs))
        else:
            fs.extend(qsort_f(*rargs))
    #print_abort_info(0.0000001)

    return fs


def wait_for_futures(fs):
    while fs:
        f = fs.pop()
        fs.extend(f())

def run(threads=2, n=20000):
    threads = int(threads)
    n = int(n)

    set_thread_pool(ThreadPool(threads))

    to_sort = range(n)
    t = 0
    for i in range(20):
        with atomic:
            random.seed(i)
            random.shuffle(to_sort)
            s = deque(to_sort)
        # qsort(s, 0, len(s))

        t -= time.time()
        # start as future, otherwise we get more threads
        # than we want (+1 for the main thread)
        fs = Future(qsort_f, s, 0, len(s), 0)
        wait_for_futures(fs())
        #assert sorted(to_sort) == list(s)
        t += time.time()

    # shutdown current pool
    set_thread_pool(None)

    return t



if __name__ == "__main__":
    run()
