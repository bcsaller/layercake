#!/usr/bin/python3.5
import argparse
import asyncio
import logging
import os

from . import discovery, ingestion, reactive


def setup():
    parser = argparse.ArgumentParser()
    parser.add_argument("-r", "--rules")
    parser.add_argument("-s", "--schemas")
    parser.add_argument("-l", "--log-level", default=logging.INFO)
    parser.add_argument("cmd", nargs="+")
    return parser.parse_args()


def configure_logging(lvl):
    logging.basicConfig(level=lvl)


def main():
    loop = asyncio.get_event_loop()
    loop.set_debug(False)
    options = setup()
    configure_logging(options.log_level)

    r = reactive.Reactive(loop=loop)
    r.load_rules(options.rules)
    r.load_schemas(options.schemas)
    try:
        loop.create_task(r())
        loop.run_forever()

        # Fork/Exec cmd
        logging.info("Container Configured")
        logging.info("Exec {}".format(options.cmd))
        os.execvp(options.cmd[0], options.cmd)
    finally:
        loop.close()

if __name__ == '__main__':
    main()
