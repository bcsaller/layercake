import unittest

from utils import local_file, Environ, O

from layer_cake import cake
from layer_cake import constants


class TestCake(unittest.TestCase):
    def test_layer_from_path(self):
        with Environ(CAKE_PATH="tests"):
            c = cake.Cake(O(layer=['disco-layer'],
                            directory="/tmp",
                            force=False,
                            layer_endpoint="fake"
                            ))
            c.fetch_all()
            assert "disco-layer" in c.layers

    def test_layer(self):
        layer = cake.Layer.from_path(local_file('disco_layer'))
        assert layer.name == "disco-layer"
        assert layer.config['name'] == "disco-layer"
        assert layer.config['author'] == "bcsaller"

    def test_bake(self):
        options = cake.setup(['bake', '-n', '-d',
                              local_file("Dockerfile.1"),
                              local_file("cake.conf")])
        df = cake.bake_main(options)
        assert "disco" in df.entrypoint['args'][0]
        assert df[-1]['args'] == ["cake", "layer", "disco-layer",
                                  "-d", constants.LAYERS_HOME]
