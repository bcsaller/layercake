import unittest
import pkg_resources
from disco.ingestion import Knowledge

class TestIngestion(unittest.TestCase):
    def test_valid_yaml(self):
        kb = Knowledge()
        kb.load(pkg_resources.resource_stream(__name__, "mysql.yaml"))
        kb.load_schema(pkg_resources.resource_stream(__name__, "interface-mysql.schema"))
        kb.validate("mysql", "mysql")
