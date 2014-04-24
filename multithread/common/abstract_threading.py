from Queue import Queue, Empty, Full
from threading import Thread, Condition, Lock
import thread, atexit, sys

try:
    from __pypy__.thread import atomic, getsegmentlimit
except ImportError:
    atomic = Lock()
    def getsegmentlimit():
        return 1


class Worker(Thread):
    """Thread executing tasks from a given tasks queue"""
    def __init__(self, queue):
        Thread.__init__(self)
        self.daemon = True
        self.queue = queue
        self.start()

    def run(self):
        while True:
            func, args, kwds = self.queue.get()
            try:
                func(*args, **kwds)
            except Exception as e:
                print e


class ThreadPool(object):
    def __init__(self, n_workers=None):
        self.input_queue = Queue()
        if n_workers is None:
            n_workers = getsegmentlimit()
        self.workers = [Worker(self.input_queue) for i in range(n_workers)]

    def add_task(self, func, *args, **kwds):
        self.input_queue.put((func, args, kwds))

    def shutdown(self):
        for w in self.workers:
            self.input_queue.put((sys.exit, (), {}))
        for w in self.workers:
            w.join()


_thread_pool = ThreadPool()
atexit.register(_thread_pool.shutdown)

def set_thread_pool(th):
    global _thread_pool
    if _thread_pool:
        _thread_pool.shutdown()
    _thread_pool = th


class Future(object):
    def __init__(self, func, *args, **kwargs):
        self._done = False
        self._result = None
        self._exception = None
        self._cond = Condition()

        assert hasattr(func, "__call__")

        _thread_pool.add_task(self._task, func, *args, **kwargs)


    def _task(self, func, *args, **kwargs):
        with self._cond:
            try:
                self._result = func(*args, **kwargs)
            except Exception as e:
                self._exception = e
            finally:
                self._done = True
                # several points/threads in the program
                # may wait for the result (notify_all):
                self._cond.notify_all()


    def __call__(self):
        with self._cond:
            while not self._done:
                self._cond.wait()

        if self._exception:
            raise self._exception

        return self._result



class AtomicFuture(Future):
    def _task(self, func, *args, **kwargs):
        with self._cond:
            try:
                with atomic:
                    self._result = func(*args, **kwargs)
            except Exception as e:
                self._exception = e
            finally:
                self._done = True
                # several points/threads in the program
                # may wait for the result (notify_all):
                self._cond.notify_all()
