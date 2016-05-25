import asyncio
import json
import logging
import os
import re
import yaml

from collections import ChainMap
from pathlib import Path

from . import discovery
from . import knowledge
from . import utils

log = logging.getLogger("disco")
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
        self._fail_ct = 0

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
        # XXX: Top level keyname to schema name is a convention that occurs
        # more than one place, Make this a formal systems rule
        interface = d.split('.')[0]
        return kb.is_valid(interface, d)

    def match(self, kb):
        exists = [kb.get(d, _marker) is not _marker for d in self.deps]
        if not self.op(exists):
            return False
        valid = [self._validate_schema(kb, d) for d in self.deps]
        if not self.op(valid):
            return False

        return True

    async def execute(self, kb, fail_limit=5):
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
        log.debug("Exec %s -> %d", self.cmd, p.returncode)
        if stdout:
            log.debug(stdout.decode('utf-8'))
        if stderr:
            log.debug(stderr.decode('utf-8'))
        self.complete = p.returncode is 0
        if not self.complete:
            self._fail_ct += 1
        if fail_limit and self._fail_ct >= fail_limit:
            raise RuntimeError(
                    "Handler failing repeatedly with valid data: {}".format(
                        self.cmd))
        return self.complete


class All(Rule):
    op = all


class Any(Rule):
    op = any


class Reactive:
    def __init__(self, config=None, loop=None):
        self.config = config or {}
        self.loop = loop if loop else asyncio.get_event_loop()
        self.rules = []
        self.kb = knowledge.Knowledge()

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
        for d in yaml.load(filelike)['rules']:
            self.add_rule(d)

    def load_schema(self, filelike):
        self.kb.load_schema(filelike)

    def find_rules(self):
        path = Path(utils.nested_get(self.config, 'disco.path', os.getcwd()))
        for fn in path.glob("*.rules"):
            self.load_rules(fn.open())

    def find_schemas(self):
        path = Path(utils.nested_get(self.config, 'disco.path', os.getcwd()))
        for fn in path.glob("*.schema"):
            self.load_schema(fn.open())

    async def run_once(self):
        complete = True
        fail_limit = int(utils.nested_get(self.config, 'disco.fail_limit', 5))
        for rule in self.rules:
            if rule.complete:
                continue
            if not rule.match(self.kb):
                log.debug("rule pending %s", rule)
                complete = False
                continue
            log.info("executing %s", rule)
            try:
                complete = await rule.execute(self.kb, fail_limit)
            except RuntimeError:
                self.shutdown()
                complete = False
                break
        return complete

    def shutdown(self):
        self._should_run = False

    async def run(self, discover):
        self._should_run = True
        interval = float(utils.nested_get(
            self.config, 'disco.interval', 1))
        while self._should_run:
            complete = await self.run_once()
            if complete:
                break
            await asyncio.sleep(interval, loop=self.loop)

        # Do any tear down on the discovery services
        await discover.shutdown()
        return complete

    async def __call__(self):
        # bring up the discovery task
        d = discovery.Discover(self.config)
        dtask = self.loop.create_task(d.watch(self.kb))
        rtask = self.loop.create_task(self.run(d))
        asyncio.wait([await dtask, await rtask])
        self.loop.stop()
        return rtask.result()
