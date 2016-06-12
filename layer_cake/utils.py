import collections
import copy


def freeze(o):
    if isinstance(o, dict):
        return frozenset({k: freeze(v) for k, v in o.items()}.items())

    if isinstance(o, list):
        return tuple([freeze(v) for v in o])

    return o


def make_hash(o):
    return hash(freeze(o))


def nested_get(dict, path, default=None, sep="."):
    o = dict
    for part in path.split(sep):
        if part not in o:
            return default
        o = o[part]
    return o


def deepmerge(dest, src):
    """
    Deep merge of two dicts.

    This is destructive (`dest` is modified), but values
    from `src` are passed through `copy.deepcopy`.
    """
    for k, v in src.items():
        if dest.get(k) and isinstance(v, dict):
            deepmerge(dest[k], v)
        else:
            dest[k] = copy.deepcopy(v)
    return dest


class NestedDict(dict):
    def __init__(self, dict_or_iterable=None, **kwargs):
        if dict_or_iterable:
            if isinstance(dict_or_iterable, dict):
                self.update(dict_or_iterable)
            elif isinstance(dict_or_iterable, collections.Iterable):
                for k, v in dict_or_iterable:
                    self[k] = v
        if kwargs:
            self.update(kwargs)

    def __setitem__(self, key, value):
        key = key.split('.')
        o = self
        for part in key[:-1]:
            o = o.setdefault(part, self.__class__())
        dict.__setitem__(o, key[-1], value)

    def __getitem__(self, path):
        o = self
        for part in path.split("."):
            if part not in o:
                raise KeyError("{} not found in {}".format(part, o))
            o = dict.__getitem__(o, part)
        return o

    def __getattr__(self, key):
        try:
            return self[key]
        except KeyError:
            raise AttributeError(key)

    def get(self, key, default=None):
        try:
            return self[key]
        except KeyError:
            return default

    def update(self, other):
        deepmerge(self, other)



