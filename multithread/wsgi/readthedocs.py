

REQUEST_LIST = [
        '/',
        ]

def make_app():
    from readthedocs import wsgi

    return wsgi.application
