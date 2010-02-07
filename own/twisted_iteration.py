
from __future__ import division

import os, sys
# really prefer PYTHONPATH
pp = os.environ.get('PYTHONPATH')
if pp:
    for ent in reversed(map(os.path.abspath, pp.split(':'))):
        sys.path.remove(ent)
        sys.path.insert(0, ent)

from twisted.python.log import err
from twisted.internet import reactor
from twisted.internet.defer import Deferred

from twisted_benchlib import Client


class Client(Client):
    def _request(self):
        self._reactor.callLater(0.0, self._continue, None)



def report(requestCount, duration):
    print (duration*10000./requestCount)


def main():
    duration = 10
    concurrency = 10

    client = Client(reactor)
    d = client.run(concurrency, duration)
    d.addCallbacks(report, err, callbackArgs=(duration,))
    d.addCallback(lambda ign: reactor.stop())
    reactor.run()



if __name__ == '__main__':
    # cheat
    import sys
    assert sys.argv[1:] == ['-n', '1']
    main()
