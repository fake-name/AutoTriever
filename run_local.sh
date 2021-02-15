#!/usr/bin/env bash

# Halt on errors.
set -e

# Run the configure script
#bash ./configure.sh include_local

if [ -f "local_configured" ]
then
	echo "Config indicator file exists. Activating and starting up!"
	python3 ./main_local.py
else
	echo "Config indicator file is missing! Cannot start!"
	exit -1;
fi;
