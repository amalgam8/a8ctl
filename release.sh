#!/bin/bash
#sudo apt-get install -y python-dev python-virtualenv
virtualenv /tmp/cli
source /tmp/cli/bin/activate
cp -R . /tmp/cli
cd /tmp/cli
python setup.py register
python setup.py install
python setup.py sdist upload
