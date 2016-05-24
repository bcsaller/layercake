import asyncio
import logging
import os
import yaml

from .utils import make_hash

log = logging.getLogger("disco")

class Source:
    """Interface for discovery sources"""
    def __init__(self, **config):
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
        """Cleanly shutdown any watches, pollers or connections"""
        pass

    async def State(self):
        """Return current state"""
        return {}


class FlatFile(Source):
    async def connect(self):
        self.state = yaml.load(open(self.config['file']))

    async def State(self):
        return self.state


class Consul(Source):
    pass


class Etcd(Source):
    pass


class Beacon(Source):
    pass



class Discover:
    def __init__(self, loop=None):
        self.loop = loop or asyncio.get_event_loop()
        self.config = {}
        self.sources = []
        self.schema = []
        self._hashes = {} #  source -> data_hash or None
        self._running = False
        self.configure()

    def configure(self):
        if self.config:
            raise RuntimeError("Don't configure disco more than once")
        self._parse()
        for source in self.config:
            if source == "disco":
                # Used to config self
                continue
            if source == "beacon":
                scls = Consul
                self.config[source].setdefault('name', 'beacon')
            elif source == "consul":
                scls = Consul
            elif source == "etcd":
                scls = Etcd
            elif source == "flat":
                scls = FlatFile
            else:
                raise ValueError("Unknown Disco Source {}".format(source))
            self.add_source(scls(**self.config[source]))

    def _parse(self):
        cfg = os.environ["DISCO_CFG"]
        config = {}
        for token in cfg.split(";"):
            kv = token.split("=", 1)
            k = kv[0]
            if len(kv) != 2:
                v = True
            else:
                v = kv[1]
            o = config
            parts = k.split(".")
            for part in parts[:-1]:
                o = o.setdefault(part, {})
            o[parts[-1]] = v
        self.config = config

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
                log.debug("Inject {}".format(state))
                knowledge.inject(state)
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
