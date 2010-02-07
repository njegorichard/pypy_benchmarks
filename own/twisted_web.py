
"""
This benchmark runs a trivial Twisted Web server and client and makes as
many requests as it can in a fixed period of time.

A significant problem with this benchmark is the lack of persistent
connections in the HTTP client.  Lots of TCP connections means lots of
overhead in the kernel that's not really what we're trying to benchmark. 
Plus lots of sockets end up in TIME_WAIT which has a (briefly) persistent
effect on system-wide performance and makes consecutive runs of the
benchmark vary wildly in their results.
"""

from __future__ import division

import os, sys
# really prefer PYTHONPATH
pp = os.environ.get('PYTHONPATH')
if pp:
    for ent in reversed(map(os.path.abspath, pp.split(':'))):
        sys.path.remove(ent)
        sys.path.insert(0, ent)

from urlparse import urlparse

import sys
f = open('P', 'w')
f.write(str(sys.path))
f.close()

from twisted.python.log import err
from twisted.python.failure import Failure
from twisted.internet import reactor
from twisted.internet.protocol import Protocol, ClientFactory
from twisted.internet.defer import Deferred
from twisted.web.server import Site
from twisted.web.static import Data
from twisted.web.resource import Resource
from twisted.web.client import ResponseDone, Agent

from twisted_benchlib import Client


class BodyConsumer(Protocol):
    def __init__(self, finished):
        self.finished = finished

    def connectionLost(self, reason):
        if reason.check(ResponseDone):
            self.finished.callback(None)
        else:
            self.finished.errback(reason)



class Client(Client):
    def __init__(self, reactor, portNumber, agent):
        self._requestLocation = 'http://127.0.0.1:%d/' % (portNumber,)
        self._agent = agent
        super(Client, self).__init__(reactor)


    def _request(self):
        d = self._agent.request('GET', self._requestLocation)
        d.addCallback(self._read)
        d.addCallback(self._continue)
        d.addErrback(self._stop)


    def _read(self, response):
        finished = Deferred()
        response.deliverBody(BodyConsumer(finished))
        return finished



def report(requestCount, duration):
    print (duration*100./requestCount)


def main():
    duration = 10
    concurrency = 10

    root = Resource()
    root.putChild('', Data("Hello, world", "text/plain"))
    port = reactor.listenTCP(
        0, Site(root), backlog=128, interface='127.0.0.1')
    agent = Agent(reactor)
    client = Client(reactor, port.getHost().port, agent)
    d = client.run(concurrency, duration)
    d.addCallbacks(report, err, callbackArgs=(duration,))
    d.addCallback(lambda ign: reactor.stop())
    reactor.run()



if __name__ == '__main__':
    # cheat
    import sys
    assert sys.argv[1:] == ['-n', '1']
    main()
