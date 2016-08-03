from pathlib import Path
from uuid import uuid4
import json


class Dockerfile(list):
    def __init__(self, source=None):
        self.source = Path(source) if source else None
        self.parse()

    def parse(self):
        if not self.source:
            return
        lines = self.source.open().readlines()
        del self[:]
        store = self.append
        walker = iter(lines)
        while True:
            # parse each line
            # we use this strange loop structure
            # to handle multiline reads
            try:
                is_json = False
                line = next(walker).rstrip()
                while True:
                    if not line.endswith("\\"):
                        break
                    line = line[:-1] + next(walker).strip()
                if line.startswith("#"):
                    TOKEN = "COMMENT"
                    ARGS = line.strip(" #")
                else:
                    TOKEN, ARGS = line.split(" ", 1)
                    if ARGS.startswith("["):
                        ARGS = json.loads(ARGS)
                        is_json = True
                store(dict(token=TOKEN, args=ARGS,
                      key=uuid4().hex, is_json=is_json))
            except StopIteration:
                break

    def find(self, token, find_all=False, reverse=False):
        seq = self
        results = []
        if reverse:
            seq = reversed(seq)
        for line in seq:
            if token == line['token']:
                if find_all is True:
                    results.append(line)
                else:
                    return line
        return results

    def replace(self, token, value, reverse=False):
        old = self.find(token, reverse=reverse)
        is_json = False
        if value and not isinstance(value, str):
            is_json = True
        else:
            if isinstance(value, str):
                value = value.strip()
        new = dict(token=token,
                   args=value,
                   key=uuid4().hex,
                   is_json=is_json)
        if old:
            # it must be replaced
            for i, line in enumerate(self):
                if old['key'] == line['key']:
                    self[i] = new
                    break
        else:
            self.append(new)

    def __getitem__(self, key):
        if isinstance(key, int):
            return super(Dockerfile, self).__getitem__(key)
        return [i['args'] for i in self.find(key, find_all=True)]

    def last(self, token):
        for i, line in reversed(list(enumerate(self))):
            if line['token'] == token:
                return i
        return None

    def add(self, cmd, args, at=None):
        is_json = False
        if isinstance(args, str) and args.startswith('['):
            args = json.loads(args)
            is_json = True
        elif not isinstance(args, str):
            is_json = True
        if at:
            def adder(x):
                self.insert(at + 1, x)
        else:
            adder = self.append
        new = dict(token=cmd, args=args, key=uuid4().hex, is_json=is_json)
        adder(new)

    @property
    def cmd(self):
        return self.find("CMD", reverse=True)

    @cmd.setter
    def cmd(self, value):
        self.replace("CMD", value, reverse=True)

    @property
    def entrypoint(self):
        return self.find("ENTRYPOINT")

    @entrypoint.setter
    def entrypoint(self, value):
        self.replace("ENTRYPOINT", value)

    def __str__(self):
        output = []
        for line in self:
            if line['token'] == "COMMENT":
                output.append("# {args}".format(**line))
            else:
                args = line['args']
                if line['is_json']:
                    args = json.dumps(line['args'])
                output.append("{} {}".format(line['token'], args))
        return "\n".join(output)
