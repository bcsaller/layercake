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
