#!/usr/bin/env python
#
# Copyright 2016 Canonical Ltd.  This software is licensed under the
# Apache License, Version 2.0
from setuptools import setup, find_packages
from layer_cake.constants import VERSION

setup(
    name='layer_cake',
    version=VERSION,
    packages=find_packages(
        exclude=["*.tests", "*.tests.*", "tests.*", "tests"]),
    # install_requires=[
        # "PyYaml",
        # "jsonschema",
        # "aioconsul",
        # "docker_py",
        # "requests",
        # "aio-etcd",
        # ],
    # dependency_links=[
        # "https://api.github.com/repos/M-o-a-T/python-aio-etcd/tarball/master#aio-etcd"
    # ],
    include_package_data=True,
    url="https://github.com/bcsaller/layercake",
    maintainer='Benjamin Saller',
    maintainer_email='benjamin.saller@canonical.com',
    description=('Service Discovery and Configuration for Application Containers'),
    license='Apache 2',
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Programming Language :: Python",
        'Programming Language :: Python :: 3.5',
    ],
    entry_points={
        'console_scripts': [
                'disco = layer_cake.disco:main',
                'cake = layer_cake.cake:main',
        ],
    },
)
