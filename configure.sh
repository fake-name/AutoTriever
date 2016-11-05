#!/usr/bin/env bash

# Halt on errors.
set -e


echo "Available branches:"
git --no-pager branch -a | cat


echo "Current release:"
git --no-pager log -1 | cat


function setup_phantomjs() {
	set +e


	# Use our local phantomjs if it appears to be intact and valid.
	tar tf ./vendored/phantomjs-2.1.1-linux-x86_64.tar.bz2
	if [ $? -eq 0 ]
	then
		echo Have pre-downloaded phantomjs. Using that.
		tar -xvf ./vendored/phantomjs-2.1.1-linux-x86_64.tar.bz2
	else
		while true; do

			rm -f phantomjs-2.1.1-linux-x86_64.tar.bz2
			rm -rf phantomjs-2.1.1-linux-x86_64

			wget https://bitbucket.org/ariya/phantomjs/downloads/phantomjs-2.1.1-linux-x86_64.tar.bz2
			tar -xvf phantomjs-2.1.1-linux-x86_64.tar.bz2 && break

			# re-enable return checking.
			echo Error downloading phantomjs!
			sleep 30
		done;
		set -e
	fi;
}


if [ -d "venv" ]
then
	echo "Venv exists. Activating!"
	source venv/bin/activate
else
	echo "No Venv! Checking dependencies are installed."
	sudo apt-get update
	sudo apt-get install build-essential -y
	sudo apt-get install libfontconfig -y
	sudo apt-get install wget -y
	sudo apt-get install libxml2 libxslt1-dev python3-dev libz-dev -y

	# Needed for chromedriver
	sudo apt-get install libnss3 -y
	sudo apt-get install libgconf2-4 -y

	# 16.04 phantomjs apt package is fucked, crashes on start.

	# Remove phantomjs from last run (if present)
	# sudo apt-get install phantomjs -y
	# wget http://cnpmjs.org/downloads/phantomjs-2.1.1-linux-x86_64.tar.bz2

	# Disable ret checking since we're manually checking the return of tar

	setup_phantomjs



	sudo mv ./phantomjs-2.1.1-linux-x86_64/bin/phantomjs /usr/local/bin/
	rm -rf phantomjs-2.1.1-linux-x86_64
	echo "Creating venv."

	python3 -m venv --without-pip venv
	wget https://bootstrap.pypa.io/get-pip.py
	./venv/bin/python3 get-pip.py
	rm get-pip.py
	source venv/bin/activate
	./venv/bin/pip install cython
	./venv/bin/pip install requests
	./venv/bin/pip install chromedriver_installer

fi;

./venv/bin/pip install --upgrade rabbitpy
./venv/bin/pip install --upgrade pika
./venv/bin/pip install --upgrade -r requirements.txt

# If we're in a docker instance, the credentials will have been passed in as a
# env var. Therefore, dump them to the settings.json file.
if [ -z "$SCRAPE_CREDS" ];
then
	echo "SCRAPE_CREDS is unset!"
else
	echo "SCRAPE_CREDS is set!"
fi;

echo "Setup OK! System is configured for launch"
