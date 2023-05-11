#!/bin/sh

sudo apt-get update && sudo apt-get install -y apt-utils

sudo apt-get update && sudo apt-get install -y build-essential

sudo apt-get update && sudo apt-get install -y python3

sudo apt-get update && sudo apt-get install -y python2

sudo apt-get update && sudo apt-get install -y pypy

alias python=python2

git clone https://github.com/Richard-Njego/pypy_benchmarks.git

cd pypy_benchmarks
./run_local.py ../pypy_splitting/pypy/bin/pyinteractive.py -o speed_splitting.json -b float,ai,richards,deltablue,eparse,fannkuch,meteor-contest,scimark_fft,spectral-norm,chaos,genshi_text,genshi_xml --fast

./run_local.py ../pypy_original/pypy/bin/pyinteractive.py -o speed_original.json -b float,ai,richards,deltablue,eparse,fannkuch,meteor-contest,scimark_fft,spectral-norm,chaos,genshi_text,genshi_xml --fast

./display_local.py  speed_splitting  speed_original