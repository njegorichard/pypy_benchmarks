import thread, sys

def f(n, lock):
    total = 0
    lst1 = ["foo"]
    for i in xrange(n):
        lst1.append(i)
        total += lst1.pop()
    sys.stdout.write('%d\n' % total)
    lock.release()


T = 4             # number of threads
N = 100000000     # number of iterations in each thread
if len(sys.argv) >= 2:
    T = int(sys.argv[1])
    if len(sys.argv) >= 3:
        N = int(sys.argv[2])

locks = []
for i in range(T):
    lock = thread.allocate_lock()
    lock.acquire()
    locks.append(lock)
    thread.start_new_thread(f, (N, lock))

for lock in locks:
    lock.acquire()
