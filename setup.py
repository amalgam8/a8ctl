from setuptools import setup

description = open('README.rst').read()

setup(
    name="a8ctl",
    version="0.1.2",
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
        "pygremlin>=0.1.3"
    ],
    license='Apache Software License V2'
)
