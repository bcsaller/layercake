import asyncio
import logging
import os
import yaml


from aioconsul import Consul
from aioconsul.exceptions import HTTPError as ConsulHTTPError
from aio_etcd import Client as EtcdClient

from .utils import make_hash

log = logging.getLogger("disco")


class Source:
    """Interface for discovery sources"""
    def __init__(self, config):
        self.name = config.get('name', self.__class__.__name__.lower())
        self.config = config

    async def connect(self):
        pass

    async def watch(self, spec):
        """
        Watch a source for change
        spec is a source specific way of slicing into
            their data.
        """
        return None

    async def disconnect(self):
        """Cleanly shutdown any watches, polls or connections"""
        pass

    async def State(self):
        """Return current state"""
        return {}


class FlatFile(Source):
    async def connect(self):
        self.state = yaml.load(open(self.config['file']))

    async def State(self):
        return self.state


class ConsulSource(Source):
    async def connect(self):
        self.client = Consul(**self.config)

    async def State(self):
        state = {}
        try:
            result = await self.client.kv.items(self.config.get('prefix', ''))
        except ConsulHTTPError:
            log.warn("Consul Error", exc_info=True)
            return state
        for k, v in result.items():
            o = state
            if "/" in k:
                parts = k.split("/")
                for p in parts[:-1]:
                    o = o.setdefault(p, {})
                k = parts[-1]
            o[k] = v
        return state


class Etcd(Source):
    async def connect(self):
        self.config['port'] = int(self.config.get('port', 4001))
        self.client = EtcdClient(**self.config)

    async def State(self):
        state = {}
        try:
            result = await self.client.read(
                    self.config.get("prefix", ""),
                    recursive=True)
        # XXX: fix exc
        except Exception as e:
            log.warn("Etcd Error %s", e, exc_info=True)
        for leaf in result.leaves:
            o = state
            if not leaf or not leaf.key:
                continue
            if "/" in leaf.key:
                parts = [p for p in leaf.key.split("/") if p]
                for p in parts[:-1]:
                    o = o.setdefault(p, {})
                k = parts[-1]
            o[k] = leaf.value
        return state


class Beacon(ConsulSource):
    pass


class Discover:
    def __init__(self, config=None, loop=None):
        self.loop = loop or asyncio.get_event_loop()
        self.config = config or {}
        self.sources = []
        self.schema = []
        self._hashes = {}  # source -> data_hash or None
        self._running = False
        self.configure()

    def configure(self):
        for source in self.config:
            if source == "disco":
                # Used to configure main application
                continue
            if source == "beacon":
                scls = ConsulSource
                self.config[source].setdefault('name', 'beacon')
            elif source == "consul":
                scls = ConsulSource
            elif source == "etcd":
                scls = Etcd
            elif source == "flat":
                scls = FlatFile
            else:
                raise ValueError("Unknown Disco Source {!r}".format(source))
            self.add_source(scls(self.config[source]))

    def add_source(self, source):
        self.sources.append(source)

    def add_schema(self, schema):
        pass

    async def populate(self, knowledge):
        """Populate knowledge base with current state from all sources"""
        for source in self.sources:
            await source.connect()
            state = await source.State()
            existing_hash = self._hashes.get(source.name, None)
            cur_hash = make_hash(state)
            if existing_hash != cur_hash:
                # Only show keys here as secrets are in the data
                log.debug("Learn {} from {}".format(
                    sorted(state.keys()),
                    source.name))
                knowledge.update(state)
                self._hashes[source.name] = cur_hash

    async def watch(self, knowledge):
        self._running = True
        while self._running:
            await self.populate(knowledge)
            await asyncio.sleep(float(self.config.get("interval", 1.0)),
                                loop=self.loop)

    async def shutdown(self):
        self._running = False
        for source in self.sources:
            await source.disconnect()
