#!/usr/bin/env bash

# This is just a very minimal script that starts the scraper.
# It's run in a screen session by the bootstrapping process.

# If we're in a vagrant environment, /vagrant will exist.
# As such, cd there. Otherwise, just run from
# the current directory.
if [ -d /vagrant ]
then
	cd /vagrant
fi

git pull .

# If we're in a docker instance, the credentials will have been passed in as a
# env var. Therefore, dump them to the settings.json file.
if [ -z "$SCRAPE_CREDS" ];
then
	echo "SCRAPE_CREDS is $SCRAPE_CREDS"
	echo "Apparently it's unset!"
else
	echo $SCRAPE_CREDS > settings.json
	echo "SCRAPE_CREDS is $SCRAPE_CREDS"
fi

python3 ./main.py
