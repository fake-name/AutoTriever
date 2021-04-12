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

install_chrome_extension () {
	preferences_dir_path="/opt/google/chrome/extensions"
	pref_file_path="$preferences_dir_path/$1.json"
	upd_url="https://clients2.google.com/service/update2/crx"
	sudo mkdir -p "$preferences_dir_path"
	echo "{" |                                       sudo tee -a "$pref_file_path"
	echo "  \"external_update_url\": \"$upd_url\"" | sudo tee -a "$pref_file_path"
	echo "}" |                                       sudo tee -a "$pref_file_path"
	echo Added \""$pref_file_path"\" ["$2"]
	sudo chmod ugo+r "$pref_file_path"
}

function setup_headless_chrome() {


	# sudo add-apt-repository ppa:saiarcot895/chromium-dev
	# sudo DEBIAN_FRONTEND=noninteractive apt-get update
	sudo DEBIAN_FRONTEND=noninteractive apt-get install -yqqq chromium-codecs-ffmpeg-extra
	# sudo DEBIAN_FRONTEND=noninteractive apt-get download chromium-browser
	# sudo dpkg -i --force-all chromium-browser*.deb

	wget -q -O - https://dl-ssl.google.com/linux/linux_signing_key.pub | sudo apt-key add -
	sudo sh -c 'echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" > /etc/apt/sources.list.d/google.list'
	sudo DEBIAN_FRONTEND=noninteractive apt-get update
	sudo DEBIAN_FRONTEND=noninteractive apt-get install google-chrome-stable -yqqq


	install_chrome_extension "cjpalhdlnbpafiamejdnhcphjbkeiagm" "ublock_origin"

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

function chrome_postinstall_remote() {
	echo "Chrome postinstall"
	sudo DEBIAN_FRONTEND=noninteractive apt-get install chromium-chromedriver -yqqq

	if [[ ! -f "/usr/local/bin/chromedriver" ]]; then
		echo "/usr/local/bin/chromedriver does not exist"
		sudo ln -s /usr/lib/chromium-browser/chromedriver /usr/local/bin/chromedriver
	fi

	# Install hourly reboot
	echo $(echo "$(($RANDOM % 60)) * * * * reboot") | sudo crontab -



}
function chrome_postinstall_local() {
	echo "Chrome postinstall"
	sudo DEBIAN_FRONTEND=noninteractive apt-get install chromium-chromedriver -yqqq

	if [[ ! -f "/usr/local/bin/chromedriver" ]]; then
		echo "/usr/local/bin/chromedriver does not exist"
		sudo ln -s /usr/local/lib/python3.8/dist-packages/chromedriver_binary/chromedriver /usr/local/bin/chromedriver
	fi

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


# Snapd is flaming garbage, and should never be installed on anything
function block_snapd() {
	echo "Package: snapd" | sudo tee -a /etc/apt/preferences.d/block-snap
	echo "Pin: release *" | sudo tee -a /etc/apt/preferences.d/block-snap
	echo "Pin-Priority: -1" | sudo tee -a /etc/apt/preferences.d/block-snap
}


function install_unit_file() {

	echo ""                           | sudo tee    "/etc/systemd/system/rwpscraper.service"
	echo "[Unit]"                     | sudo tee -a "/etc/systemd/system/rwpscraper.service"
	echo "Description=foo"            | sudo tee -a "/etc/systemd/system/rwpscraper.service"
	echo "StartLimitInterval=0"       | sudo tee -a "/etc/systemd/system/rwpscraper.service"
	echo "StartLimitIntervalSec=0"    | sudo tee -a "/etc/systemd/system/rwpscraper.service"
	echo ""                           | sudo tee -a "/etc/systemd/system/rwpscraper.service"
	echo "[Service]"                  | sudo tee -a "/etc/systemd/system/rwpscraper.service"
	echo "User=scrapeworker"          | sudo tee -a "/etc/systemd/system/rwpscraper.service"
	echo "WorkingDirectory=/scraper"  | sudo tee -a "/etc/systemd/system/rwpscraper.service"
	echo "Type=simple"                | sudo tee -a "/etc/systemd/system/rwpscraper.service"
	echo "RestartSec=10"              | sudo tee -a "/etc/systemd/system/rwpscraper.service"
	echo "Restart=always"             | sudo tee -a "/etc/systemd/system/rwpscraper.service"
	echo "ExecStart=/scraper/run.sh"  | sudo tee -a "/etc/systemd/system/rwpscraper.service"
	echo ""                           | sudo tee -a "/etc/systemd/system/rwpscraper.service"
	echo "[Install]"                  | sudo tee -a "/etc/systemd/system/rwpscraper.service"
	echo "WantedBy=multi-user.target" | sudo tee -a "/etc/systemd/system/rwpscraper.service"

	sudo systemctl enable rwpscraper.service
	sudo systemctl start rwpscraper.service

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

	block_snapd

	if [ "$is_local" = true ] ; then
		go_local_install
		chrome_postinstall_local
	else
		do_remote_install
		chrome_postinstall_remote
		install_unit_file
	fi

	echo "Setup OK! System is configured for launch"

}


go $@
