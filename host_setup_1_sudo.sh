#!/bin/bash

# Prompts user to change default editor (e.g., to vim)
#update-alternatives --config editor

# Update the machine (might upgrade kernel too)
#apt-get update
#apt-get upgrade

LIST_OF_APPS="\
htop \
screen \
byobu \
git \
python3 \
python3-pip \
linux-image-extra-$(uname -r) \
aufs-tools \
zip \
"

# Install needed packages
apt-get update
apt-get install -y ${LIST_OF_APPS}

pip3 install virtualenv
pip3 install virtualenvwrapper

# Install latest version of Docker (ideally 1.9+)
program='docker'
if ! prog_loc="$(which $program)" || [ -z "$prog_loc" ]; then
    wget -qO- https://get.docker.com/ | sh
fi

pip3 install docker-compose

# Install docker-compose auto-complete
# (which will be pip installed in virtualenv
if ! [ -f "/etc/bash_completion.d/docker-compose" ]
then
    curl -L \
    https://raw.githubusercontent.com/docker/compose/$(docker-compose --version | \
    awk 'NR==1{print $NF}')/contrib/completion/bash/docker-compose > \
    /etc/bash_completion.d/docker-compose
fi

