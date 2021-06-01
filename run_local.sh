#!/usr/bin/env bash

# Halt on errors.
set -e


if [ -f "local_configured" ]
then
	echo "Config indicator file exists. Skipping setup!"
else
	echo "Config indicator file is missing! Doing setup!"
	# Run the configure script
	bash ./configure.sh include_local
fi;


python3 ./main_local.py
