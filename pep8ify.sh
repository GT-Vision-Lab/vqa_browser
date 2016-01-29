#!/bin/bash

# Deals with making a backup when there are sub-directories
# Might break with weird filenames (e.g., spaces, weird characters)
#[[ "$1" == */* ]]
#cp --backup=numbered "${1%/*}"/"${1##*/}" "${1%/*}"/._"${1##*/}".bak
cp --backup=numbered $1{,.bak}
autopep8 --in-place --aggressive --aggressive $1
