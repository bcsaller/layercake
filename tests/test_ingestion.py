import unittest

from utils import local_stream
from disco.ingestion import Knowledge

class TestIngestion(unittest.TestCase):
    def test_valid_yaml(self):
        kb = Knowledge()
        kb.load(local_stream("mysql.yaml"))
        kb.load_schema(local_stream("interface-mysql.schema"))
        kb.validate("mysql", "mysql")
