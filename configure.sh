#!/usr/bin/env bash

# Halt on errors.
set -e


echo "Available branches:"
git --no-pager branch -a | cat


echo "Current release:"
git --no-pager log -1 | cat



function setup_headless_chrome() {

	# sudo add-apt-repository ppa:saiarcot895/chromium-dev
	# sudo apt-get update
	# sudo apt-get install -y chromium-codecs-ffmpeg-extra
	# sudo apt-get download chromium-browser
	# sudo dpkg -i --force-all chromium-browser*.deb

	wget -q -O - https://dl-ssl.google.com/linux/linux_signing_key.pub | sudo apt-key add -
	sudo sh -c 'echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" >> /etc/apt/sources.list.d/google.list'
	sudo apt-get update
	sudo apt-get install google-chrome-stable -y
	sudo apt-get install chromium-chromedriver -y

	sudo ln -s /usr/lib/chromium-browser/chromedriver /usr/local/bin/chromedriver

	curl https://raw.githubusercontent.com/StevenBlack/hosts/master/hosts | sudo tee -a /etc/hosts

	# set +e
	# tar tf ./vendored/MinimalHeadless.tar.gz
	# if [ $? -eq 0 ]
	# then
	# 	echo Have Headless Chromium. Extracting.
	# 	tar -xvf ./vendored/MinimalHeadless.tar.gz
	# fi;
	# set -e
}

if [ -d "venv" ]
then
	echo "Venv exists. Activating!"
	source venv/bin/activate
else
	echo "No Venv! Checking dependencies are installed."
	sudo apt-get update
	# sudo apt-get dist-upgrade -y
	sudo apt-get install build-essential -y

	# Apparently at least one VPS host has separated git from build-essential?
	sudo apt-get install git -y
	sudo apt-get install libfontconfig -y
	sudo apt-get install wget -y
	sudo apt-get install htop -y
	sudo apt-get install libxml2 -y
	sudo apt-get install libxslt1-dev -y
	sudo apt-get install python3-dev -y
	sudo apt-get install python3-dbg -y
	sudo apt-get install libz-dev -y


	# Needed for chromedriver
	sudo apt-get install libnss3 -y
	sudo apt-get install libgconf2-4 -y

	# 16.04 phantomjs apt package is fucked, crashes on start.

	# Remove phantomjs from last run (if present)
	# sudo apt-get install phantomjs -y
	# wget http://cnpmjs.org/downloads/phantomjs-2.1.1-linux-x86_64.tar.bz2

	# Disable ret checking since we're manually checking the return of tar


	setup_headless_chrome

	echo "Creating venv."
	python3 -m venv --without-pip venv
	wget https://bootstrap.pypa.io/get-pip.py
	./venv/bin/python3 get-pip.py --force-reinstall
	./venv/bin/pip install six
	# ./venv/bin/pip install cython
	./venv/bin/pip install requests
	./venv/bin/pip install chromedriver_installer
	./venv/bin/pip install git+https://github.com/berkerpeksag/astor.git
	source venv/bin/activate
	rm get-pip.py

fi;

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
