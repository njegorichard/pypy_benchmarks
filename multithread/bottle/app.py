from common.abstract_threading import atomic, Future, set_thread_pool, ThreadPool
from BaseHTTPServer import HTTPServer

import threading, time

from wsgiref.simple_server import WSGIRequestHandler

class ThreadedHTTPServer(HTTPServer):
    """Handle requests in a separate thread."""
    application = None
    allow_reuse_address = True

    def server_bind(self):
        """Override server_bind to store the server name."""
        HTTPServer.server_bind(self)
        self.setup_environ()

    def setup_environ(self):
        # Set up base environment
        env = self.base_environ = {}
        env['SERVER_NAME'] = self.server_name
        env['GATEWAY_INTERFACE'] = 'CGI/1.1'
        env['SERVER_PORT'] = str(self.server_port)
        env['REMOTE_HOST']=''
        env['CONTENT_LENGTH']=''
        env['SCRIPT_NAME'] = ''

    def get_app(self):
        return self.application

    def set_app(self,application):
        self.application = application

    def process_request(self, request, client_address):
        def worker(request, client_address):
            try:
                self.finish_request(request, client_address)
            except:
                self.handle_error(request, client_address)
            finally:
                self.close_request(request)
        Future(worker, request, client_address)



import bottle
import subprocess, sys, os

class ThreadedServer(bottle.ServerAdapter):
    def run(self, app): # pragma: no cover
        srv = ThreadedHTTPServer((self.host, self.port), WSGIRequestHandler)
        srv.set_app(app)
        srv.serve_forever()


@bottle.route('/')
def index():
    time.sleep(0.5)
    return "hi from " + threading.currentThread().getName()


def run(threads=4, runtime=10, clients=8):
    threads = int(threads)
    runtime = int(runtime)
    clients = int(clients)
    PORT = 21634

    set_thread_pool(ThreadPool(threads))

    def bottle_server():
        bottle.run(server=ThreadedServer,
                   host='localhost', port=PORT)

    bs = threading.Thread(target=bottle_server)
    bs.setDaemon(True)
    bs.start()

    print "wait for startup"
    time.sleep(5)
    print "hopefully ready now"

    try:
        print "execute openload:"
        p = subprocess.Popen(['openload',
                              '-l', str(runtime),
                              '-o', 'CSV',
                              'localhost:%s' % PORT, str(clients)],
                             stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE)
    except OSError as e:
        sys.stderr.write("Error trying to execute 'openload'\n%s" % e)
        os.exit(1)

    returncode = p.wait()
    out, err = p.communicate()
    if returncode != 0:
        sys.stderr.write("'openload' returned an error\n%s" % e)
        os.exit(1)
    print out, err

if __name__ == "__main__":
    run()
