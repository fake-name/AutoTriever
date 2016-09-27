#!/usr/bin/env bash

# Halt on errors.
set -e

# This is just a very minimal script that starts the scraper.
echo "Updating local git repo"
git fetch --all
git pull

# Run the configure script
bash ./configure.sh

if [ -d "venv" ]
then
	echo "Venv exists. Activating and starting up!"
	source venv/bin/activate
	python3 ./main.py
else
	echo "Venv is missing! Cannot start!"
	exit -1;
fi;