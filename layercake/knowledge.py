import jsonschema
import logging
import yaml

from .utils import NestedDict

log = logging.getLogger("disco")


class Knowledge(NestedDict):
    """Nested Dict like composite of knowledge from
    any available sources"""

    def load(self, filelike, to=None):
        data = yaml.load(filelike)
        if to:
            d = data
            for p in reversed(to.split(".")):
                d = {p: d}
            data = d
        self.update(data)
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
            # Don't show the full validation error because
            # it might expose secrets to the log
            logging.info("Failed to validate {}: {}".format(schema, e.message))
            return False
        except KeyError:
            return False
        return True
