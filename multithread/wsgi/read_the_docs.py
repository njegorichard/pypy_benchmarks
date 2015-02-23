import os
import sys

import readthedocs
from readthedocs import wsgi


REQUEST_LIST = [
        '/',
        ]


def make_app():
    sys.path.append(os.path.dirname(readthedocs.__file__))

    return wsgi.application
