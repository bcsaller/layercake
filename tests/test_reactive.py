import unittest
import pkg_resources

from utils import local_stream

from layercake.knowledge import Knowledge
from layercake import reactive


class TestReactive(unittest.TestCase):
    def test_rule(self):
        kb = Knowledge()
        kb.load(local_stream("mysql.yaml"))
        kb.load_schema(local_stream("interface-mysql.schema"))
        rule = reactive.Rule(['mysql'], 'mysql-configure')
        self.assertTrue(rule.match(kb))
        rule = reactive.Rule(['pgsql'], 'pgsql-configure')
        self.assertFalse(rule.match(kb))

        rule = reactive.Any(['pgsql', 'mysql'], 'db-configure')
        self.assertTrue(rule.match(kb))

        rule = reactive.All(['pgsql', 'mysql'], 'db-configure')
        self.assertFalse(rule.match(kb))

    def test_reactive(self):
        r = reactive.Reactive()
        r.load_rules(pkg_resources.resource_stream(__name__, "myapp1.rules"))
        self.assertEqual(len(r.rules), 1)
