import unittest

from utils import local_file
from layercake.dockerfile import Dockerfile


class TestDockerfile(unittest.TestCase):
    def test_dockerfile(self):
        df = Dockerfile(local_file("Dockerfile.1"))
        assert df.cmd['args'] == "ps aux"
        assert df.entrypoint['args'] == ["/bin/bash"]
        assert df['MAINTAINER'] == ["none"]
        assert df['LABEL'] == ['version="1.0"', 'description="Multi line"']

    def test_dockerfile_mutation(self):
        df = Dockerfile(local_file("Dockerfile.1"))
        df.cmd = df.entrypoint['args']
        df.entrypoint = ["/usr/bin/disco"]
        assert df.entrypoint['args'] == ["/usr/bin/disco"]
        assert df.cmd['args'] == ["/bin/bash"]
