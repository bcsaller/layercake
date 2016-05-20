import unittest
import pkg_resources

from disco.ingestion import Knowledge
from disco import reactive


class TestReactive(unittest.TestCase):
    def test_rule(self):
        kb = Knowledge()
        kb.load(pkg_resources.resource_stream(__name__, "mysql.yaml"))
        kb.load_schema(pkg_resources.resource_stream(__name__, "interface-mysql.schema"))
        rule = reactive.Rule(['mysql'], 'mysql-configure')
        self.assertTrue(rule.match(kb))
        rule = reactive.Rule(['pgsql'], 'pgsql-configure')
        self.assertFalse(rule.match(kb))

        rule = reactive.Any(['pgsql', 'mysql'], 'db-configure')
        self.assertTrue(rule.match(kb))

        rule = reactive.All(['pgsql', 'mysql'], 'db-configure')
        self.assertFalse(rule.match(kb))

    def test_reactive(self):
        pass
