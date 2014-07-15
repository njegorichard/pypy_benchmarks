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
            if xs[l] < pivot:
                l += 1
                continue
            if xs[r] > pivot:
                r -= 1
                continue
            xs[l], xs[r] = xs[r], xs[l]
        l += 1
        r -= 1

    fs = []
    #right_amount = 1000 > n // 2 > 505
    right_amount = level == 4
    if right_amount:
        fs.append(Future(qsort_f, xs, l0, r - l0 + 1, level+1))
        fs.append(Future(qsort_f, xs, l, l0 + n - l, level+1))
    else:
        fs.extend(qsort_f(xs, l0, r - l0 + 1, level+1))
        fs.extend(qsort_f(xs, l, l0 + n - l, level+1))
    #print_abort_info(0.0000001)

    return fs


def wait_for_futures(fs):
    while fs:
        f = fs.pop()
        fs.extend(f())

def run(threads=2, n=100000):
    threads = int(threads)
    n = int(n)

    set_thread_pool(ThreadPool(threads))


    to_sort = range(n)
    random.seed(121)
    random.shuffle(to_sort)
    s = deque(to_sort)
    # qsort(s, 0, len(s))

    fs = qsort_f(s, 0, len(s), 0)
    wait_for_futures(fs)


    # shutdown current pool
    set_thread_pool(None)



if __name__ == "__main__":
    run()
