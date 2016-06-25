#!/usr/bin/env bash

# Halt on errors.
set -e

# This is just a very minimal script that starts the scraper.
echo "Updating local git repo"
git fetch --all
git pull

# Run the configure scrip
bash ./configure.sh

echo "Launching executable."
python3 ./main.py
