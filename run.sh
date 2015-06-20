#!/usr/bin/env bash

# Halt on errors.
set -e

# This is just a very minimal script that starts the scraper.
echo "Updating local git repo"
git pull .

echo "Current release:"
git log -1

# If we're in a docker instance, the credentials will have been passed in as a
# env var. Therefore, dump them to the settings.json file.
if [ -z "$SCRAPE_CREDS" ];
then
	echo "SCRAPE_CREDS is unset!"
else
	echo "SCRAPE_CREDS is set!"
fi;

echo "Launching executable."
python3 ./main.py
