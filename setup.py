# Copyright 2016 IBM Corporation
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.

from setuptools import setup

description = open('README.rst').read()

setup(
    name="a8ctl",
    version="0.1.7",
    description="Amalgam8 Command Line Interface",
    long_description=description,
    author='Amalgam8 Team',
    url='https://github.com/amalgam8/a8ctl',
    packages=["a8ctl", "a8ctl.v1"],
    entry_points = {
        "console_scripts": ['a8ctl = a8ctl.v1.a8ctl:main']
    },
    include_package_data=True,
    install_requires=[
        "argparse",
        "requests",
        "parse",
        "prettytable",
        "decorator",
        "pygremlin>=0.1.3"
    ],
    license='Apache Software License V2'
)
