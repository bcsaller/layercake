import asyncio
import logging
import os
from . import ingestion

_marker = object()


class Rule:
    op = all

    def __init__(self, deps, command):
        self._complete = False
        # Once complete the rule shouldn't be run again
        self.once = True
        # List of data paths that must be available
        # and validate by their schema
        self.deps = deps
        self.cmd = command

    def __str__(self):
        return "{} :: {}".format(" ".join(self.deps),
                                 self.cmd)

    @property
    def complete(self):
        return self._complete and self.once

    @complete.setter
    def complete(self, value):
        self._complete = bool(value)

    def match(self, kb):
        # XXX: await the lock on the KB
        def validate_schema(d):
            # XXX: This is a convention that occurs
            # more than one place, Make this a
            # formal systems rule
            interface = d.split('.')[0]
            return kb.is_valid(interface, d)

        exists = [kb.get(d, _marker) is not _marker for d in self.deps]
        if not self.op(exists):
            return False

        valid = [validate_schema(d) for d in self.deps]
        if not self.op(valid):
            return False

        return True

    async def execute(self):
        asyncio.create_subprocess_exec(self.cmd)
        ec = await p.wait()
        if ec is not 0:
            # XXX clean up
            raise OSError


class All(Rule):
    op = all


class Any(Rule):
    op = any


class Reactive:
    def __init__(self, cmd, loop=None):
        self.cmd = cmd
        self.loop = loop if loop else asyncio.get_event_loop()
        self.rules = []
        self.kb = ingestion.Knowledge()


    async def run_once(self):
        complete = True
        for rule in rules:
            if rule.complete:
                continue
            if not rule.match(self.kb):
                complete = False
                continue
            await rule.execute()
        return complete

    async def run(self):
        while True:
            complete = await self.run_once()
            if complete:
                break

        # Do any tear down on the discovery services
        #self.discovery.shutdown()
        # Fork/Exec cmd
        logging.info("Container Configured")
        logging.info("Exec {}".format(self.cmd))
        os.exec(self.cmd)

