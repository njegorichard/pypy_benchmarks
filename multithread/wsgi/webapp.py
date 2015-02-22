import os
import sys
import threading

from urllib2 import urlopen
from wsgi_intercept import (
    urllib_intercept, add_wsgi_intercept, remove_wsgi_intercept
)

host, port = 'localhost', 80
url = 'http://{0}:{1}/'.format(host, port)
settings = {}

def init(benchmark, request_count="100", *args):
    settings["request_count"] = int(request_count)

    bm_module = type(sys)("bm_module")
    file_name = os.path.join(os.path.dirname(__file__), benchmark + ".py")
    execfile(file_name, bm_module.__dict__)

    if not hasattr(bm_module, 'REQUEST_LIST'):
        print 'request list not defined'
        sys.exit(-1)
    if not hasattr(bm_module, 'make_app'):
        print 'app maker not defined'
        sys.exit(-1)

    settings["bm_module"] = bm_module

    # set up intercepter
    urllib_intercept.install_opener()
    add_wsgi_intercept(host, port, bm_module.make_app)

    return args

def run(thread_count="2"):
    # test
    threads = []
    for i in range(int(thread_count)):
        thread = threading.Thread(target=do_requests, args=(settings['request_count'],))
        thread.start()
        threads.append(thread)

    for thread in threads:
        thread.join()


def do_requests(request_count):
    for i in range(request_count):
        for request in settings["bm_module"].REQUEST_LIST:
            request_url = url + request
            stream = urlopen(url)
            content = stream.read()


if __name__ == '__main__':
    init(sys.argv[1])
    run()
