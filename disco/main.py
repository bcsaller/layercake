#!/usr/bin/python3.5
import argparse
import asyncio
import logging
import logging.handlers
import os

from . import reactive

log = logging.getLogger("disco")


def setup():
    parser = argparse.ArgumentParser()
    parser.add_argument("-p", "--path",
                        help="Path for disco files (*.rules, *.schema)",
                        default=os.getcwd())
    parser.add_argument("-l", "--log-level", default=logging.INFO)
    parser.add_argument("cmd", nargs="+")
    return parser.parse_args()


def configure_logging(lvl):
    logging.basicConfig(
            format="%(asctime)s: %(module)s.%(funcName)s:%(lineno)s: %(message)s",  # noqa
            datefmt="%Y-%m-%d:%T",
            #  handlers=[logging.handlers.SysLogHandler()],
            level=lvl)


def main():
    loop = asyncio.get_event_loop()
    loop.set_debug(False)
    options = setup()
    configure_logging(options.log_level)

    r = reactive.Reactive(loop=loop)
    r.find_rules(options.path)
    r.find_schemas(options.path)
    try:
        loop.create_task(r())
        loop.run_forever()

        # Fork/Exec cmd
        log.info("Container Configured")
        log.info("Exec {}".format(options.cmd))
        os.execvp(options.cmd[0], options.cmd)
    finally:
        loop.close()

if __name__ == '__main__':
    main()
