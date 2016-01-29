#!/bin/bash

dir=~/.virtualenvs
if [ ! -d $dir ]; then
    mkdir $dir
fi

# Source venv
export VIRTUALENVWRAPPER_PYTHON=/usr/bin/python3
source /usr/local/bin/virtualenvwrapper.sh

mkvirtualenv py3-project
source "~/.virtualenvs/py3-project/bin/activate" 

# Install also python programs needed on host
pip install -r requirements_host.txt
