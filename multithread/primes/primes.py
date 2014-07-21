# -*- coding: utf-8 -*-

# from https://github.com/Tinche/stm-playground


import sys
import time, random
from common.abstract_threading import (
    atomic, Future, set_thread_pool, ThreadPool,
    hint_commit_soon, print_abort_info)

from itertools import izip, chain, repeat

from Queue import Queue
from pyprimes import isprime
import threading

def check_prime(num):
    return isprime(num), num


def grouper(n, iterable, padvalue=None):
    "grouper(3, 'abcdefg', 'x') --> ('a','b','c'), ('d','e','f'), ('g','x','x')"
    return izip(*[chain(iterable, repeat(padvalue, n-1))]*n)


poison_pill = object()

def worker(tasks, results):
    while True:
        batch = tasks.get()
        if batch is poison_pill:
            tasks.task_done()
            return

        result = []
        for task in batch:
            with atomic:
                result.append(check_prime(task))
        results.put(result)

        tasks.task_done()



def run(threads=2, n=2000000):
    threads = int(threads)
    n = int(n)

    LIMIT = n
    BATCH_SIZE = 1000

    tasks = Queue()
    results = Queue()
    print("Starting...")

    with atomic:
        for batch in grouper(BATCH_SIZE, xrange(LIMIT), 1):
            tasks.put(list(batch))
        for _ in xrange(threads):
            tasks.put(poison_pill)

    for _ in xrange(threads):
        t = threading.Thread(target=worker, args=(tasks, results))
        t.start()
    tasks.join()

    count = 0
    while not results.empty():
        batch_results = results.get()
        count += sum(1 for res in batch_results if res[0])

    return count



if __name__ == "__main__":
    run()
