from contextlib import contextmanager
import pkg_resources
import os


def local_stream(name):
    return pkg_resources.resource_stream(__name__, name)


def local_file(name):
    return pkg_resources.resource_filename(__name__, name)


@contextmanager
def Environ(**kwargs):
    orig = os.environ.copy()
    replace = set(kwargs.keys()) & set(orig.keys())
    removes = set(kwargs.keys()) - set(orig.keys())
    try:
        os.environ.update(kwargs)
        yield
    finally:
        for r in removes:
            os.environ.pop(r)
        for r in replace:
            os.environ[r] = orig[r]


class O(dict):
    def __getattr__(self, key):
        return self[key]
