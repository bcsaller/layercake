import argparse
import json
import logging
import os
import shutil
import subprocess
import tempfile

import requests
import yaml

from collections import OrderedDict
from io import BytesIO
from pathlib import Path

from . import dockerfile
from .constants import LAYERS_HOME
from .disco import configure_logging
from .utils import nested_get

from docker import Client as DockerClient

log = logging.getLogger("cake")


def layer_get_metadata(
        name,
        api="http://layer-cake.io",
        apiver="api/v2",
        apiendpoint="layers"):
    uri = "/".join([api, apiver, apiendpoint, name])
    try:
        log.debug("Fetching Layer information %s", uri)
        result = requests.get(uri)
    except:
        result = None
    if result and result.ok:
        result = result.json()
        if result.get("repo"):
            return result
    raise ValueError("Unable to locate layer {} using {}".format(
                    name, uri))


def git(*cmd, **kwargs):
    return subprocess.check_call(["git", *cmd], **kwargs)


class Layer:
    def __init__(self, metadata):
        self.metadata = metadata
        self.dir = None
        self._config = {}

    @classmethod
    def from_path(cls, path):
        ins = cls({})
        ins.dir = path
        return ins

    @property
    def config(self):
        if self._config:
            return self._config
        if not self.dir:
            raise OSError("Layer %s has not be fetched")
        cfg = Path(self.dir) / "layer.yaml"
        if cfg.exists():
            data = yaml.load(cfg.open())
            if 'layer' not in data:
                raise ValueError("%s doesn't appear to be a layer config" % cfg)
            self._config = data['layer']
        else:
            self._config = {}
        return self._config

    @property
    def name(self):
        return self.config['name']

    def fetch(self, todir, overwrite_target=False):
        repo = self.metadata['repo']
        name = self.metadata['id']
        subpath = self.metadata.get('repopath', '/')
        if subpath.startswith("/"):
            subpath = subpath[1:]
        # pull the repo to a tempdir
        # then select any subpath, moving that to the target dir
        self.dir = Path(todir) / name
        if self.dir.exists():
            if overwrite_target:
                shutil.rmtree(str(self.dir))
            else:
                raise OSError(
                  "Fetch of {} would overwrite {}. Use -f to force".format(
                    name,
                    self.dir))

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
            # XXX: this could fail across certain types of mounts
            target.rename(self.dir)

    def install(self, layerdir):
        installer = self.dir / "install"
        shutil.copytree(str(self.dir), str(layerdir / self.name))
        if installer.exists():
            output = subprocess.check_output(str(installer.resolve()))
            log.info("Executed installer for %s", self.name)
            log.debug(output.decode("utf-8"))


class Cake:
    def __init__(self, options):
        self.layer_names = options.layer
        self.directory = Path(options.directory)
        self.force_overwrite = options.force
        self.api_endpoint = options.layer_endpoint.rstrip("/")
        self.scan_cakepath()

    def fetch_layer(self, name, resolving):
        if resolving.get(name):
            return resolving[name]
        layer = None
        if name in self.cake_map:
            # Construct and register a layer from the
            # directory
            layer = Layer.from_path(self.cake_map[name])
        elif layer is None:
            metadata = layer_get_metadata(name, api=self.api_endpoint)
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
        # This will fill out the resolving map when layers have deps they add
        # them to the map and this loop will resolve them keeping the deps in
        # proper order.
        resolving = OrderedDict([[n, None] for n in self.layer_names])
        if not self.directory.exists():
            self.directory.mkdir(parents=True)
        while not all(resolving.values()):
            for name, layer in resolving.items():
                if layer is not None:
                    continue
                self.fetch_layer(name, resolving)
        self.layers = resolving

    def scan_cakepath(self):
        cake_map = {}  # layername -> Path
        CAKE_PATH = os.environ.get("CAKE_PATH", "")
        CAKE_PATH = CAKE_PATH.split(":")
        CAKE_PATH = [Path(p) for p in CAKE_PATH]
        if CAKE_PATH:
            for cake_segment in [p for p in CAKE_PATH if p.exists()]:
                # Build a last write wins map of layer to directory information
                # we can search for the name of the layer in this path ignoring
                # the repo (and the repo subpath, as finding the layers.yaml in
                # a nested structure without metadata is too intensive)
                p = Path(cake_segment)
                for layerdir in p.iterdir():
                    cfg = layerdir / "layer.yaml"
                    if layerdir.is_dir() and cfg.exists():
                        # This appears to be a layer
                        cfg = yaml.load(cfg.open())
                        layername = nested_get(cfg, "layer.name")
                        cake_map[layername] = layerdir

        self.cake_map = cake_map
        log.debug("Found local Layers %s", sorted(self.cake_map.items()))

    def install(self):
        # There are some implicit rules used during the install
        # layer install will copy *.{schema,rules} to layerdir
        layerdir = Path(LAYERS_HOME).mkdir(
                parents=True, exist_ok=True)
        for layer in self.layers.values():
            layer.install(layerdir)


def layer_main(options):
    "Pull a layer from the api endpoint or from CAKE_PATH"
    endpoint = os.environ.get("LAYERCAKE_API")
    if endpoint:
        options.layer_endpoint = endpoint
    cake = Cake(options)
    cake.fetch_all()
    if options.no_install:
        return
    cake.install()


def bake_main(options):
    """Munge a dockerfile from a cfg

    cake:
        layers: []
    """
    endpoint = os.environ.get("LAYERCAKE_API")
    if endpoint:
        options.layer_endpoint = endpoint

    config = yaml.load(open(options.config))['cake']
    df = dockerfile.Dockerfile(options.dockerfile)

    if options.layer_endpoint:
        df.add("ENV", "LAYERCAKE_API={}".format(options.layer_endpoint))

    # In this mode we are adding run cmds for each
    # layer in the cfg file (those may pull other layers)
    # then we output a new docker file and docker build the
    # new container.
    last_run = df.last("RUN")
    df.add("RUN", ['pip3', 'install', '--upgrade', 'layer_cake'], at=last_run)
    for layer_name in config['layers']:
        last_run = df.last("RUN")
        df.add("RUN", ["cake", "layer", layer_name,
               "-d", LAYERS_HOME],
               at=last_run)

    # we might have an entrypoint
    # or a command (or both)
    if df.entrypoint:
        df.entrypoint = ["disco"] + df.entrypoint['args']

    log.debug("Using Dockerfile\n%s", str(df))
    if not options.no_build:
        client = DockerClient()
        f = BytesIO(str(df).encode("utf-8"))
        response = client.build(fileobj=f, tag="layercake/disco", decode=True)
        for line in response:
            if 'errorDetail' in line:
                log.critical(line['errorDetail']['message'].strip())
            elif 'stream' in line:
                log.info(line['stream'].strip())
    else:
        return df


def search_main(options):
    endpoint = os.environ.get("LAYERCAKE_API")
    if endpoint:
        options.layer_endpoint = endpoint

    url = "{}/api/v2/layers/".format(options.layer_endpoint)
    query = {"q": options.term}
    result = requests.get(url, query)
    if not result.ok:
        print("Unable to connect to layer endpoint")
        return
    data = result.json()
    if options.format == "json":
        print(json.dumps(data, indent=2))
    elif options.format == "yaml":
        print(yaml.dump(data))
    else:
        print("{:<10} {:<10} {}".format("Id", "Name", "Descrption"))
        for item in data:
            print("{id:<10} {name:<10} {summary}".format(**item))


def setup(args=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("-l", "--log-level", default=logging.INFO)
    parser.set_defaults(func=lambda options: parser.print_help())

    parsers = parser.add_subparsers()
    layer = parsers.add_parser("layer", help=layer_main.__doc__.split("\n", 1)[0])
    layer.add_argument("--layer-endpoint",
            help="API endpoint for metadata",
            default="http://layer-cake.io")
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
    layer.set_defaults(func=layer_main)

    baker = parsers.add_parser("bake", help=bake_main.__doc__.split("\n", 1)[0])
    baker.add_argument("-d", "--dockerfile",
                       help="Dockerfile to process",
                       )
    baker.add_argument("-n", "--no-build", action="store_true",
                       help="Don't build Dockerfile")
    baker.add_argument("config",
                       nargs="?",
                       default="cake.conf")
    baker.set_defaults(func=bake_main)

    search = parsers.add_parser("search")
    search.add_argument("--layer-endpoint",
            help="API endpoint for metadata",
            default="http://layer-cake.io")
    search.add_argument("-f", "--format", default="text", help="Options text|json|yaml")
    search.add_argument("term", nargs="+")
    search.set_defaults(func=search_main)

    options = parser.parse_args(args)
    return options


def main():
    options = setup()
    configure_logging(options.log_level)
    options.func(options)

if __name__ == '__main__':
    main()
