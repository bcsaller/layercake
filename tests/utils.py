import pkg_resources


def local_stream(name):
    return pkg_resources.resource_stream(__name__, name)
