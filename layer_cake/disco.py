#!/usr/bin/python3.5
import argparse
import asyncio
import logging
import logging.handlers
import os
import yaml

from .constants import LAYERCAKE_DIR
from . import reactive

log = logging.getLogger("disco")


def setup():
    parser = argparse.ArgumentParser()
    parser.add_argument("-l", "--log-level", default=logging.INFO)
    parser.add_argument("-c", "--conf", default="{}/disco.conf".format(LAYERCAKE_DIR))
    parser.add_argument("cmd", nargs="+")
    return parser.parse_args()


def configure_logging(lvl):
    logging.basicConfig(
            format="%(asctime)s: %(name)s %(module)s.%(funcName)s:%(lineno)s: %(message)s",  # noqa
            datefmt="%Y-%m-%d:%T",
            #  handlers=[logging.handlers.SysLogHandler()],
            level=lvl)
    logging.getLogger("aioconsul.request").setLevel(logging.WARNING)
    logging.getLogger("aio_etcd.client").setLevel(logging.WARNING)
    logging.getLogger("requests").setLevel(logging.WARNING)


def configure_from_file(name=None):
    config = {'disco': {'path': LAYERCAKE_DIR}}
    if name and os.path.exists(name):
        config.update(yaml.load(open(name, 'r')))
    return config


def configure_from_env(envstr=None):
    cfg = envstr or os.environ.get("DISCO_CFG", "")
    config = {}
    for token in cfg.split("|"):
        token = token.strip()
        if not token:
            continue
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
    return config


def main():
    loop = asyncio.get_event_loop()
    loop.set_debug(False)
    options = setup()
    configure_logging(options.log_level)
    config = configure_from_file(options.conf)
    config.update(configure_from_env())
    r = reactive.Reactive(config, loop=loop)
    r.find_rules()
    r.find_schemas()
    try:
        config_task = loop.create_task(r())
        loop.run_until_complete(config_task)
        if config_task.result() is True:
            # Fork/Exec cmd
            log.info("Container Configured")
            log.info("Exec {}".format(options.cmd))
            os.execvp(options.cmd[0], options.cmd)
        else:
            log.critical("Unable to configure container, see log or run with -l DEBUG")
    finally:
        loop.close()

if __name__ == '__main__':
    main()
