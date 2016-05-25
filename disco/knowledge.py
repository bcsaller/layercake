import jsonschema
import logging
import yaml

from collections import ChainMap

log = logging.getLogger("disco")


class Knowledge:
    """Nested Dict like composite of knowledge from
    any available sources"""

    def __init__(self):
        self.map = ChainMap()

    def __repr__(self):
        return str(self.map)

    def load(self, filelike, to=None):
        data = yaml.load(filelike)
        if to:
            d = data
            for p in reversed(to.split(".")):
                d = {p: d}
            data = d
        self.inject(data)
        return self

    def inject(self, data):
        self.map = self.map.new_child(data)
        return self

    def load_schema(self, filelike):
        pos = filelike.tell()
        data = yaml.load(filelike)
        filelike.seek(pos)
        name = data['name']
        self.load(filelike, "schemas.{}".format(name))

    def validate(self, schema, path=None):
        schema = self['schemas.{}'.format(schema)]
        obj = self[path] if path else self.map
        jsonschema.validate(obj, schema)
        logging.debug("Validated {}".format(schema['name']))

    def is_valid(self, schema, path=None):
        try:
            self.validate(schema, path)
        except jsonschema.ValidationError as e:
            logging.debug(exc_info=e)
            return False
        except KeyError:
            return False

        return True

    def get(self, key, default=None):
        try:
            return self[key]
        except KeyError:
            return default

    def __getitem__(self, key):
        o = self.map
        for part in key.split('.'):
            o = o[part]
        return o
