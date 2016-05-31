import argparse
import logging
import shutil
import subprocess
import tempfile

import requests
import yaml

from collections import OrderedDict
from pathlib import Path


def layer_get_metadata(
        name,
        #api="http://interfaces.juju.solutions",
        api="http://localhost:9999",
        apiver="api/v2",
        apiendpoint="layer"):
    uri = "/".join([api, apiver, apiendpoint, name])
    try:
        # Filter the results to only those layers which are
        # targeted to runC containers
        result = requests.get(uri, params={"q": "kind:runC"})
    except:
        result = None
    if result and result.ok:
        result = result.json()
        if result.get("repo"):
            return result
    raise ValueError("Unable to locate layer {}".format(
                    name))


def git(*cmd, **kwargs):
    return subprocess.check_call(["git", *cmd], **kwargs)


class Layer:
    def __init__(self, metadata):
        self.metadata = metadata
        self.dir = None
        self._config = {}

    def fetch(self, todir, overwrite_target=False):
        repo = self.metadata['repo']
        name = self.metadata['name']
        subpath = self.metadata.get('repopath', '/')
        if subpath.startswith("/"):
            subpath = subpath[1:]
        # pull the repo to a tempdir
        # then select any subpath, moving that to the target dir
        with tempfile.TemporaryDirectory() as td:
            d = Path(td)
            reponame = repo.split("/")[-1]
            if reponame.endswith(".git"):
                reponame = reponame[:-4]
            target = d / reponame
            git("clone", repo, str(target))
            if subpath:
                target = d / subpath
                if not target.exists() or not target.is_dir():
                    raise OSError(
                        "Repo subpath {} invalid, unable to continue".format(
                            name))
            self.dir = Path(todir) / name
            # XXX: this could fail across certain types of mounts
            if self.dir.exists():
                if overwrite_target:
                    shutil.rmtree(str(self.dir))
                else:
                    raise OSError(
                      "Fetch of {} would overwrite {}. Use -f to force".format(
                        name,
                        self.dir))
            target.rename(self.dir)

    @property
    def config(self):
        if self._config:
            return self._config
        if not self.dir:
            raise OSError("Layer %s has not be fetched")
        cfg = Path(self.dir) / "layer.yaml"
        if cfg.exists():
            self._config = yaml.load(cfg.open())
        else:
            self._config = {}
        return self._config


class Cake:
    def __init__(self, options):
        self.layer_names = options.layer
        self.directory = options.directory
        self.force_overwrite = options.force

    def fetch_layer(self, name, resolving):
        if resolving.get(name):
            return resolving[name]
        metadata = layer_get_metadata(name)
        layer = Layer(metadata)
        layer.fetch(self.directory, self.force_overwrite)
        # Now create a resolving entry for any layers this includes
        for dep in layer.config.get('layers', []):
            if dep not in resolving:
                resolving[dep] = None
            # Each request implies the layer is the dep of a predecessor,
            # so move it to the front of the list with the intention
            # of installing it before the thing that depends on it
            resolving.move_to_end(dep, False)
        resolving[name] = layer
        return layer

    def fetch_all(self):
        resolving = OrderedDict([[n, None] for n in self.layer_names])
        while not all(resolving.values()):
            for name, layer in resolving.items():
                if layer is not None:
                    continue
                self.fetch_layer(name, resolving)
        self.layers = resolving

    def install(self):
        pass


def setup():
    parser = argparse.ArgumentParser()
    parser.add_argument("-l", "--log-level", default=logging.INFO)
    parsers = parser.add_subparsers()
    layer = parsers.add_parser("layer")
    layer.add_argument("-d", "--directory", default=Path.cwd())
    layer.add_argument("-f", "--force", action="store_true",
                        help=("Force overwrite of existing layers "
                              "in directory (-d)"))
    layer.add_argument("-n", "--no-install", action="store_true",
                        help=("when set exit after pulling layers, "
                              "and before the install phase"))

    layer.add_argument(
            "layer",
            nargs="+",
            help=("The name of the layer to include, if more "
                  "than one is provided they will be included in order"))
    layer.set_defaults(func=layer)


    baker = parsers.add_parser("bake")
    baker.add_argument("-d", "--dockerfile",
                       help="Dockerfile to process",
                       )
    baker.add_argument("config",
                        nargs="?",
                        default="cake.conf")
    baker.set_defaults(func=bake)

    options = parser.parse_args()
    return options


def setupLogging(options):
    logging.basicConfig(level=options.log_level)


def layer(options):
    cake = Cake(options)
    cake.fetch_all()
    if options.no_install:
        return
    cake.install()


def bake(options):
    config = yaml.locad(open(options.config))
    df = Dockerfile(options.dockerfile)

    # In this mode we are adding run cmds for each
    # layer in the cfg file (those may pull other layers)
    # then we output a new docker file and docker build the
    # new container.


def main():
    options = setup()
    setupLogging(options)
    options.func(options)

if __name__ == '__main__':
    main()
