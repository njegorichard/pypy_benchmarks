from common.abstract_threading import atomic, Future, set_thread_pool, ThreadPool
from SocketServer import ThreadingMixIn
from BaseHTTPServer import HTTPServer, BaseHTTPRequestHandler

import threading, socket, time

from wsgiref.simple_server import WSGIRequestHandler, WSGIServer

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



from bottle import route, run, ServerAdapter

class ThreadedServer(ServerAdapter):
    def run(self, app): # pragma: no cover
        srv = ThreadedHTTPServer((self.host, self.port), WSGIRequestHandler)
        srv.set_app(app)
        srv.serve_forever()


@route('/')
def index():
    time.sleep(0.5)
    return "hi from " + threading.currentThread().getName()


if __name__ == "__main__":
    set_thread_pool(ThreadPool(8))
    run(server=ThreadedServer, # debug=True,
        host='localhost', port=8080)
