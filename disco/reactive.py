import asyncio
import glob
import json
import logging
import os
import re
import yaml
from collections import ChainMap

from . import discovery
from . import ingestion

log = logging.getLogger("reactive")
_marker = object()


class Rule:
    op = all

    def __init__(self, deps, command, once=True):
        self._complete = False
        # Once complete the rule shouldn't be run again
        self.once = once
        # List of data paths that must be available
        # and validate by their schema
        self.deps = deps
        self.cmd = command

    def __repr__(self):
        return "{}({}) -> {}".format(
                self.op.__name__,
                " ".join(self.deps),
                self.cmd)

    @property
    def complete(self):
        return self._complete and self.once

    @complete.setter
    def complete(self, value):
        self._complete = bool(value)

    def _validate_schema(self, kb, d):
        # XXX: This is a convention that occurs
        # more than one place, Make this a
        # formal systems rule
        interface = d.split('.')[0]
        return kb.is_valid(interface, d)


    def match(self, kb):
        # XXX: await the lock on the KB
        exists = [kb.get(d, _marker) is not _marker for d in self.deps]
        if not self.op(exists):
            return False

        valid = [self._validate_schema(kb, d) for d in self.deps]
        if not self.op(valid):
            return False

        return True

    async def execute(self, kb):
        """Call the handler, the convention here is
        that all matched rules will be available as
        JSON data written to the handlers STDIN.

        This means if you match interface 'foo'
        foo will be passed to the handler as JSON.
        """
        data = ChainMap()
        for d in self.deps:
            interface = d.split('.')[0]
            if self._validate_schema(kb, d):
                data = data.new_child(kb.get(interface))

        data = json.dumps(dict(data)).encode('utf-8')
        p = await asyncio.create_subprocess_exec(
                self.cmd,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
                )
        stdout, stderr = await p.communicate(data)
        if p.returncode is not 0:
            # XXX clean up
            raise OSError


class All(Rule):
    op = all


class Any(Rule):
    op = any


class Reactive:
    def __init__(self, loop=None):
        self.loop = loop if loop else asyncio.get_event_loop()
        self.rules = []
        self.kb = ingestion.Knowledge()

    def add_rule(self, definition):
        # simple rule parser
        defs = definition.get("when", "")
        op = any if defs.startswith("any:") else all
        if defs.startswith("any:") or defs.startswith("all:"):
            defs = defs[4:]
        defs = re.split(",\s*", defs)
        cmd = definition["do"]

        rule = Rule(defs, cmd)
        rule.op = op
        self.rules.append(rule)
        return rule

    def load_rules(self, filelike):
        if isinstance(filelike, str):
            filelike = open(filelike, "r")
        for d in yaml.load(filelike)['rules']:
            self.add_rule(d)

    def find_rules(self):
        for fn in glob.glob("*.rules"):
            self.load_rules(fn)

    def load_schemas(self, schemas):
        if isinstance(schemas, str):
            schemas = open(schemas, "r")
        self.kb.load_schema(schemas)

    async def run_once(self):
        complete = True
        for rule in self.rules:
            if rule.complete:
                continue
            if not rule.match(self.kb):
                log.debug("rule pending %s", rule)
                complete = False
                continue
            log.info("executing %s", rule)
            await rule.execute(self.kb)
        return complete

    async def run(self, discover):
        while True:
            complete = await self.run_once()
            if complete:
                break

        # Do any tear down on the discovery services
        await discover.shutdown()

    async def __call__(self):
        # bring up the discovery task
        d = discovery.Discover()
        self.find_rules()
        dtask = self.loop.create_task(d.watch(self.kb))
        rtask = self.loop.create_task(self.run(d))
        await dtask
        await rtask
        self.loop.stop()

