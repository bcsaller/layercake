import asyncio
import os
import pkg_resources
import unittest

from utils import local_file, Environ

from disco import discovery
from disco.ingestion import Knowledge


class TestDiscovery(unittest.TestCase):
    def test_discovery_cfg(self):
        with Environ(DISCO_CFG="consul.host=foo;consul.user=bar"):
            d = discovery.Discover()
        self.assertEquals(d.config, {"consul": {
            "host": "foo", "user": "bar"}})


    def test_discovery(self):
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        self.loop.set_debug(False)

        with Environ(DISCO_CFG="flat.file={}".format(
                local_file("mysql.yaml"))):
            d = discovery.Discover()
            # low-level API to directly populate
            kb = Knowledge()
            self.loop.run_until_complete(d.populate(kb))
            self.assertEqual(kb['mysql.host'], "localhost:3306")
