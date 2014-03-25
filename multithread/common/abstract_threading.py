from Queue import Queue, Empty, Full
from threading import Thread, Condition, Lock
import thread

try:
    from __pypy__.thread import atomic
except ImportError:
    atomic = Lock()

class Worker(Thread):
    """Thread executing tasks from a given tasks queue"""
    def __init__(self, queue):
        Thread.__init__(self)
        self.daemon = True
        self.next_task = None
        self.cond = Condition()
        self.queue = queue
        self.start()

    def run(self):
        # the next line registers the at_commit_cb on interpreter
        # level for this thread. This should be fixed in the 
        # interpreter (it causes a conflict in stmgcintf.register_at_commit_cb).
        # thread.at_commit(lambda : 0, ())

        while True:
            with self.cond:
                while self.next_task is None:
                    self.cond.wait()

                func, args, kargs = self.next_task
                self.next_task = None

                try:
                    func(*args, **kargs)
                except Exception as e:
                    print e

            # first time put in queue by threadpool on creation
            try:
                self.queue.put_nowait(self)
            except Full:
                # thread limit reached, I'll show myself out..
                return


class ThreadPool(object):
    def __init__(self, thread_queue_size=12):
        self.threads = Queue(thread_queue_size)

    def add_task(self, func, *args, **kargs):
        try:
            worker = self.threads.get_nowait()
        except Empty:
            worker = Worker(self.threads)

        with worker.cond:
            worker.next_task = (func, args, kargs)
            worker.cond.notify_all()




import multiprocessing
_thread_pool = ThreadPool(3 * multiprocessing.cpu_count())




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
