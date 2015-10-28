#!/usr/bin/env bash

# Halt on errors.
set -e

# This is just a very minimal script that starts the scraper.
echo "Updating local git repo"
git fetch . origin/master
git pull . origin/master

echo "Current release:"
git --no-pager log -1 | cat

if [ -d "venv" ]
then
	echo "Venv exists. Activating!"
	source venv/bin/activate
else
	echo "No Venv! Creating."
	virtualenv -p python3 venv
	source venv/bin/activate
	pip install -r requirements.txt

fi;

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
