#!/usr/bin/env python
#
# Copyright 2016 Canonical Ltd.  This software is licensed under the
# Apache License, Version 2.0
#from pip.req import parse_requirements
from setuptools import setup, find_packages

# ignored for now, we include a git repo directly
#install_reqs = parse_requirements("requirements.txt", session=False)
#reqs = [str(ir.req) for ir in install_reqs]

setup(
    name='layercake',
    version="0.1.0",
    packages=find_packages(
        exclude=["*.tests", "*.tests.*", "tests.*", "tests"]),
    install_requires=[],
    include_package_data=True,
    maintainer='Benjamin Saller',
    maintainer_email='benjamin.saller@canonical.com',
    description=('Service Discovery and Configuration for Application Containers'),
    license='Apache 2',
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Programming Language :: Python",
    ],
    entry_points={
        'console_scripts': [
                'disco = layercake.disco:main',
                'cake = layercake.cake:main',
        ],
    },
)
