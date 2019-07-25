#!/usr/bin/env bash

# Halt on errors.
set -e

export DEBIAN_FRONTEND="noninteractive"

function report_git() {
	echo "Available branches:"
	git --no-pager branch -a | cat


	echo "Current release:"
	git --no-pager log -1 | cat

}


function setup_headless_chrome() {

	# sudo add-apt-repository ppa:saiarcot895/chromium-dev
	# sudo DEBIAN_FRONTEND=noninteractive apt-get update
	# sudo DEBIAN_FRONTEND=noninteractive apt-get install -yqqq chromium-codecs-ffmpeg-extra
	# sudo DEBIAN_FRONTEND=noninteractive apt-get download chromium-browser
	# sudo dpkg -i --force-all chromium-browser*.deb

	wget -q -O - https://dl-ssl.google.com/linux/linux_signing_key.pub | sudo apt-key add -
	sudo sh -c 'echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" > /etc/apt/sources.list.d/google.list'
	sudo DEBIAN_FRONTEND=noninteractive apt-get update
	sudo DEBIAN_FRONTEND=noninteractive apt-get install google-chrome-stable -yqqq
	sudo DEBIAN_FRONTEND=noninteractive apt-get install chromium-chromedriver -yqqq

	if [[ ! -f "/usr/local/bin/chromedriver" ]]; then
		echo "/usr/local/bin/chromedriver does not exist"
		sudo ln -s /usr/lib/chromium-browser/chromedriver /usr/local/bin/chromedriver
	fi

	curl https://raw.githubusercontent.com/StevenBlack/hosts/master/hosts | sudo tee -a /etc/hosts

	# Install ublock
	sudo mkdir -p /etc/opt/chrome/policies/managed

	# Try to install ublock origin
	sudo tee -a /etc/opt/chrome/policies/managed/master_preferences << END
{
 "extensions": {
    "settings": {
       "cjpalhdlnbpafiamejdnhcphjbkeiagm": {
          "location": 1,
          "manifest": {
            "content_scripts": [ {
              "all_frames": true,
              "js": [ "js/vapi-client.js", "js/contentscript.js" ],
              "matches": [ "http://*/*", "https://*/*" ],
              "run_at": "document_start"
              } ],
             "key": "MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEAmJNzUNVjS6Q1qe0NRqpmfX/oSJdgauSZNdfeb5RV1Hji21vX0TivpP5gq0fadwmvmVCtUpOaNUopgejiUFm/iKHPs0o3x7hyKk/eX0t2QT3OZGdXkPiYpTEC0f0p86SQaLoA2eHaOG4uCGi7sxLJmAXc6IsxGKVklh7cCoLUgWEMnj8ZNG2Y8UKG3gBdrpES5hk7QyFDMraO79NmSlWRNgoJHX6XRoY66oYThFQad8KL8q3pf3Oe8uBLKywohU0ZrDPViWHIszXoE9HEvPTFAbHZ1umINni4W/YVs+fhqHtzRJcaKJtsTaYy+cholu5mAYeTZqtHf6bcwJ8t9i2afwIDAQAB",
             "name": "uBlock Origin",
             "permissions": [ "contextMenus", "privacy", "storage", "tabs", "unlimitedStorage", "webNavigation", "webRequest", "webRequestBlocking", "<all_urls>" ],
             "update_url": "https://clients2.google.com/service/update2/crx",
             "version": "0.0"
          },
          "path": "cjpalhdlnbpafiamejdnhcphjbkeiagm\\0.0",
          "state": 1
       }
    }
  }
}
END

	sudo tee -a /etc/opt/chrome/policies/managed/master_preferences.json << END
{
 "extensions": {
    "settings": {
       "cjpalhdlnbpafiamejdnhcphjbkeiagm": {
          "location": 1,
          "manifest": {
            "content_scripts": [ {
              "all_frames": true,
              "js": [ "js/vapi-client.js", "js/contentscript.js" ],
              "matches": [ "http://*/*", "https://*/*" ],
              "run_at": "document_start"
              } ],
             "key": "MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEAmJNzUNVjS6Q1qe0NRqpmfX/oSJdgauSZNdfeb5RV1Hji21vX0TivpP5gq0fadwmvmVCtUpOaNUopgejiUFm/iKHPs0o3x7hyKk/eX0t2QT3OZGdXkPiYpTEC0f0p86SQaLoA2eHaOG4uCGi7sxLJmAXc6IsxGKVklh7cCoLUgWEMnj8ZNG2Y8UKG3gBdrpES5hk7QyFDMraO79NmSlWRNgoJHX6XRoY66oYThFQad8KL8q3pf3Oe8uBLKywohU0ZrDPViWHIszXoE9HEvPTFAbHZ1umINni4W/YVs+fhqHtzRJcaKJtsTaYy+cholu5mAYeTZqtHf6bcwJ8t9i2afwIDAQAB",
             "name": "uBlock Origin",
             "permissions": [ "contextMenus", "privacy", "storage", "tabs", "unlimitedStorage", "webNavigation", "webRequest", "webRequestBlocking", "<all_urls>" ],
             "update_url": "https://clients2.google.com/service/update2/crx",
             "version": "0.0"
          },
          "path": "cjpalhdlnbpafiamejdnhcphjbkeiagm\\0.0",
          "state": 1
       }
    }
  }
}
END

	# set +e
	# tar tf ./vendored/MinimalHeadless.tar.gz
	# if [ $? -eq 0 ]
	# then
	# 	echo Have Headless Chromium. Extracting.
	# 	tar -xvf ./vendored/MinimalHeadless.tar.gz
	# fi;
	# set -e
}

function do_remote_install() {
	report_git

	if [ -d "venv" ]
	then
		echo "Venv exists. Activating!"
		source venv/bin/activate
	else
		echo "No Venv! Checking dependencies are installed."
		sudo DEBIAN_FRONTEND=noninteractive apt-get update
		# sudo DEBIAN_FRONTEND=noninteractive apt-get dist-upgrade -yqqq
		sudo DEBIAN_FRONTEND=noninteractive apt-get install build-essential -yqqq

		# Apparently at least one VPS host has separated git from build-essential?
		sudo DEBIAN_FRONTEND=noninteractive apt-get install git -yqqq
		sudo DEBIAN_FRONTEND=noninteractive apt-get install libfontconfig -yqqq
		sudo DEBIAN_FRONTEND=noninteractive apt-get install wget -yqqq
		sudo DEBIAN_FRONTEND=noninteractive apt-get install htop -yqqq
		sudo DEBIAN_FRONTEND=noninteractive apt-get install libxml2 -yqqq
		sudo DEBIAN_FRONTEND=noninteractive apt-get install libxslt1-dev -yqqq
		sudo DEBIAN_FRONTEND=noninteractive apt-get install python3-dev -yqqq
		sudo DEBIAN_FRONTEND=noninteractive apt-get install python3-dbg -yqqq
		sudo DEBIAN_FRONTEND=noninteractive apt-get install libz-dev -yqqq
		sudo DEBIAN_FRONTEND=noninteractive apt-get install curl -yqqq


		# Needed for chromedriver
		sudo DEBIAN_FRONTEND=noninteractive apt-get install libnss3 -yqqq
		sudo DEBIAN_FRONTEND=noninteractive apt-get install libgconf2-4 -yqqq

		# 16.04 phantomjs apt package is fucked, crashes on start.

		# Remove phantomjs from last run (if present)
		# sudo DEBIAN_FRONTEND=noninteractive apt-get install phantomjs -yqqq
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
		./venv/bin/pip install chromedriver-binary
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

}

function go_local_install() {

	if [ -f "local_configured" ]
	then
		echo "Already set up!"
	else
		echo "No config indicator file! Checking dependencies are installed."
		sudo DEBIAN_FRONTEND=noninteractive apt-get update
		# sudo DEBIAN_FRONTEND=noninteractive apt-get dist-upgrade -yqqq
		sudo DEBIAN_FRONTEND=noninteractive apt-get install build-essential -yqqq

		# Apparently at least one VPS host has separated git from build-essential?
		sudo DEBIAN_FRONTEND=noninteractive apt-get install git -yqqq
		sudo DEBIAN_FRONTEND=noninteractive apt-get install libfontconfig -yqqq
		sudo DEBIAN_FRONTEND=noninteractive apt-get install wget -yqqq
		sudo DEBIAN_FRONTEND=noninteractive apt-get install htop -yqqq
		sudo DEBIAN_FRONTEND=noninteractive apt-get install libxml2 -yqqq
		sudo DEBIAN_FRONTEND=noninteractive apt-get install libxslt1-dev -yqqq
		sudo DEBIAN_FRONTEND=noninteractive apt-get install python3-dev -yqqq
		sudo DEBIAN_FRONTEND=noninteractive apt-get install python3-dbg -yqqq
		sudo DEBIAN_FRONTEND=noninteractive apt-get install libz-dev -yqqq
		sudo DEBIAN_FRONTEND=noninteractive apt-get install curl -yqqq


		# Needed for chromedriver
		sudo DEBIAN_FRONTEND=noninteractive apt-get install libnss3 -yqqq
		sudo DEBIAN_FRONTEND=noninteractive apt-get install libgconf2-4 -yqqq

		setup_headless_chrome

		echo "Doing setup."
		python3 -m venv --without-pip venv
		wget https://bootstrap.pypa.io/get-pip.py
		sudo python3 get-pip.py --force-reinstall
		sudo pip install six
		sudo pip install cython
		sudo pip install requests
		sudo pip install chromedriver-binary
		sudo pip install git+https://github.com/berkerpeksag/astor.git
		rm get-pip.py

		sudo pip install --upgrade -r requirements.txt
		sudo pip install --upgrade -r local_requirements.txt

		touch local_configured
	fi;

	# If we're in a docker instance, the credentials will have been passed in as a
	# env var. Therefore, dump them to the settings.json file.
	if [ -z "$SCRAPE_CREDS" ];
	then
		echo "SCRAPE_CREDS is unset!"
	else
		echo "SCRAPE_CREDS is set!"
	fi;

	echo "Setup OK! System is configured for launch"

}


function go() {

	is_local=false

	for i in "$@" ; do
		echo "Var: $i"
		if [[ $i == "include_local" ]] ; then
			echo "Local!"
			is_local=true
			break
		fi
	done


	if [ "$is_local" = true ] ; then
		go_local_install
	else
		do_remote_install
	fi

}


go $@
