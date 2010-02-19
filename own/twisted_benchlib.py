
from twisted.internet.defer import Deferred

class Client(object):
    def __init__(self, reactor):
        self._reactor = reactor
        self._requestCount = 0


    def run(self, concurrency, duration):
        self._reactor.callLater(duration, self._stop, None)
        self._finished = Deferred()
        for i in range(concurrency):
            self._request()
        return self._finished


    def _continue(self, ignored):
        self._requestCount += 1
        self._request()


    def _stop(self, reason):
        if self._finished is not None:
            finished = self._finished
            self._finished = None
            if reason is not None:
                finished.errback(reason)
            else:
                finished.callback(self._requestCount)

def driver(f):
    from twisted.internet import reactor
    d = f(reactor)
    reactor.callWhenRunning(d.addBoth, lambda ign: reactor.stop())
    reactor.run()

def multidriver(*f):
    from twisted.internet import reactor
    jobs = iter(f)
    def work():
        for job in jobs:
            d = job(reactor)
            d.addCallback(lambda ignored: work())
            return
        reactor.stop()
    reactor.callWhenRunning(work)
    reactor.run()
