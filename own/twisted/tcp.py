
"""
This benchmarks runs a trivial Twisted TCP echo server and a client pumps as
much data to it as it can in a fixed period of time.

The size of the string passed to each write call may play a significant
factor in the performance of this benchmark.
"""

from __future__ import division

from twisted.internet.defer import Deferred
from twisted.internet.protocol import ServerFactory, ClientCreator, Protocol
from twisted.protocols.wire import Echo

from benchlib import driver


class Counter(Protocol):
    count = 0

    def dataReceived(self, bytes):
        self.count += len(bytes)



class Client(object):
    _finished = None

    def __init__(self, reactor, port):
        self._reactor = reactor
        self._port = port


    def run(self, duration, chunkSize):
        self._duration = duration
        self._bytes = 'x' * chunkSize
        # Set up a connection
        cc = ClientCreator(self._reactor, Counter)
        d = cc.connectTCP('127.0.0.1', self._port)
        d.addCallback(self._connected)
        return d


    def _connected(self, client):
        self._client = client
        self._stopCall = self._reactor.callLater(self._duration, self._stop)
        client.transport.registerProducer(self, False)
        self._finished = Deferred()
        return self._finished


    def _stop(self):
        self.stopProducing()
        self._client.transport.unregisterProducer()
        self._finish(self._client.count)


    def _finish(self, value):
        if self._finished is not None:
            finished = self._finished
            self._finished = None
            finished.callback(value)


    def resumeProducing(self):
        self._client.transport.write(self._bytes)


    def stopProducing(self):
        self._client.transport.loseConnection()


    def connectionLost(self, reason):
        self._finish(reason)


 
def main(reactor, duration):
    chunkSize = 16384

    server = ServerFactory()
    server.protocol = Echo
    serverPort = reactor.listenTCP(0, server)
    client = Client(reactor, serverPort.getHost().port)
    d = client.run(duration, chunkSize)
    return d


if __name__ == '__main__':
    import sys
    import tcp
    driver(tcp.main, sys.argv)
