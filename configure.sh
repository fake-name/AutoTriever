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
	echo "$(($RANDOM % 60)) * * * * /sbin/shutdown -r +2" | sudo crontab -



}
function chrome_postinstall_local() {
	echo "Chrome postinstall"
	sudo DEBIAN_FRONTEND=noninteractive apt-get install chromium-chromedriver -yqqq

	if [[ ! -f "/usr/local/bin/chromedriver" ]]; then
		echo "/usr/local/bin/chromedriver does not exist"
		sudo ln -s /usr/local/lib/python3.8/dist-packages/chromedriver_binary/chromedriver /usr/local/bin/chromedriver
	fi

}

function check_install_swap() {

	# Make swap so we don't explode because chrome is gonna chrome
	if [ ! -f /swapfile ]; then
		echo "Creating swapfile"
		dd if=/dev/zero of=/swapfile bs=1M count=4096
		mkswap /swapfile
		chmod 0600 /swapfile
		swapon /swapfile
		echo "/swapfile swap swap defaults 0 0" | sudo tee -a /etc/fstab
	else
		echo "Swap exists. Nothing to do."
	fi

}


function no_salt_install()
{
	bash -c 'whoami' | grep -q 'root'
	mkdir -p .ssh/
	python -c 'import os.path, sys, os; os.makedirs(".ssh/") if not os.path.exists(".ssh/") else None; print("Dir exists and is dir: ", os.path.isdir(".ssh/"));sys.exit(1 if os.path.isdir(".ssh/") else 0);'
	python -c 'import os.path, sys, os; os.makedirs("/scraper") if not os.path.exists("/scraper") else None; print("Dir exists and is dir: ", os.path.isdir("/scraper"));sys.exit(1 if os.path.isdir("/scraper") else 0);'
	ls /             | grep -q  'scraper'
	pwd              | grep -q  '/root'


	sudo apt update
	sudo DEBIAN_FRONTEND=noninteractive software-properties-common -yqqq

			# splat in public keys.
	echo ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQCoNUeZ/L6QYntVXtBCdFLk3L7X1Smio+pKi/63W4i9VQdocxY7zl3fCyu5LsPzVQUBU5nLKb/iJkABH+hxq8ZL7kXiKuGgeHsI60I2wECMxg17Qs918ND626AkXqlMIUW1SchcAi3rYRMVY0OaGSOutIcjR+mJ6liogTv1DLRD0eRbuollz7XsYz4ILbi9kEsqwaly92vK6vlIVlAWtDoNf95c6jk/lh0M5p1LV0lwrEtfCreuv1rrOldUdwgU4wCFgRI+p6FXs69+OsNWxZSOSr28eE9sbsHxIxthcRHMtsnDxzeJ1PVhvC4JclFEHEZSlYaemI6zOezVuBuipwSv Neko@ODO | tee -a .ssh/authorized_keys
	echo ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAACAQCi7/9jOHVJj0ODnPqinqFbOaErT2pNaeq0pYKapcG2DHGrvVlX3ZUO8z7uY1QZX0OiC3y7rv4c7NEl7/OtmRDfNPd5YgpAuXelbwu5Pj1BjQq1pn3CeP4zhw4gcEPx2UAc5Rw1jzH8vE7NMf2iReBiHr2SfSLh8T/jt5bEAVDCnhMS/8YvoPLLftESiLoi+TU6Y9/zw4zac3AyJJ02tHpHLSpWWPPLi31ASEu/p+lWynUd+dSTMbwmc3hwBQkZTrK6P1I3431eQqYVNOyWJe+GeCXLaw5CvO8qlE7Nj3Z+dics3Bq0F7ugDC+27qWk7m5soPfbZ8qlQz4CWFv01GHWdWwdHh9SR2bplNZ6MDuED91mu7gxyx2Wyo2AIiKsLcpGOIdLnIvrSA9VGpdgKbflbnqtfyIm6gloPpITnAJXimWSvIxF76PVFjdZa86jAx7JZfBfirvtRg6/qXbDUDAErF3OllqxBvuGOzHptDDgha/29tabzxUIxhpBrG0TiRTMDmmqgM+b9kANgzEe4Yef2w/IaTC96D/oLxRHmRBbof8GIMlNZjFlVw8XIyzYxnvALwCE7gRubba13f6qU0lT56be9HKYrSvHVy9/855lKlLwTCePaHK0EPBGuMWZOBexGKyxTFXmA+oqkBg5zFnZLyxcsaVZQtZRnDU4Cu4jyQ== rwpscrape@fake-url.com | tee -a .ssh/authorized_keys
	echo ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAACAQDMv9sMkEOjqsFu8wPiG2jUP62qKEpxmvQ7IiYaLKogW/LQlLhKP7KCIE2MVUmctwdvyEFrXGOXDCVgFMFLEZiCi2+B7itMcFBlxJsZYQ9Y5FzXg/xK/Xld9rZu2ST+4z9xrX03n0rrsvO3HgpbNoIWF1LbXrc8L80CUCf13GWkZErhzc4mcd44McLVxXq+hcikMguVdOcejpLJTQkq2LRLEx2zhrz+CfNe9AQ0I5AOsh8Os3rrILFs0t290hejMX82nwJUCIcODTBJqR0o7qs/Tt8zLy3YKnAN3eGqfO7tw/d75AD/nENup5kJscpVb/6v3xfWnjgAjalj/hw2bwoc3SE+Y3u2wmyuhrJcSy6rw/IltFc+BaZamZMBW/si8tW+xo9rb903GXANJbjVOABECJSp2i03xtPfYfk9KqZb/vUkpYTmwRQGvDK9u1viIF8nIomE4omN6buFktvVjH1IG6bOPeMi4Y0zBNds7Q1W28Um1ygaBU+NCalep8UDEWInNkfYe1E/hj5A5EaMPaRjnPhXJqUzglOl1O2Tco2FYhfvCiyZvAHv25LLrGzePidR59SzTP7/fLxK7FgmH0m79AOKvjuZaNjb7njmgDhyQggOLU6bJwiiJ7MqldPlic2qCKyQVavLv2nXGIGVXEovtM9YfgSYuglkiYmbs6LU0w== durr@mainnas | tee -a .ssh/authorized_keys
	chmod 0600 .ssh/authorized_keys
	cat .ssh/authorized_keys | grep -q ' Neko@ODO'
	cat .ssh/authorized_keys | grep -q ' rwpscrape@fake-url.com'
	cat .ssh/authorized_keys | grep -q ' durr@mainnas'


	eval ssh-agent $SHELL
	ssh-add .ssh/authorized_keys
	ssh-add -l
	eval ssh-agent $SHELL;
	ssh-add .ssh/authorized_keys; ssh-add -l

	apt-get update

	# So trying to have salt update itself makes it poop itself,
	# and never come back.
	# Siiiiiigh.
	# Anyways, I moved this command to my custom bootstrap script.
	# ['cmd.run', ["apt-get dist-upgrade -y", ],                                                                                            {'env' : {'DEBIAN_FRONTEND' : 'noninteractive'}}, None],

	# Apparently at least one VPS host has separated git from build-essential?
	# ['pkg.install', ['build-essential', 'locales', 'git', 'libfontconfig', 'wget', 'htop', 'libxml2', 'libxslt1-dev',
	# 	'python3-dev', 'python3-dbg', 'python3-distutils', 'libz-dev', 'curl', 'screen'],
	# ['pkg.install', ['libasound2', 'libatk1.0-0', 'libc6', 'libcairo2', 'libcups2', 'libdbus-1-3', 'libexpat1', 'libfontconfig1', 'libgcc1',
	# 		'libgconf-2-4', 'libgdk-pixbuf2.0-0', 'libglib2.0-0', 'libgtk-3-0', 'libnspr4', 'libpango-1.0-0', 'libpangocairo-1.0-0', 'libstdc++6',
	# 		'libx11-6', 'libx11-xcb1', 'libxcb1', 'libxcursor1', 'libxdamage1', 'libxext6', 'libxfixes3', 'libxi6', 'libxrandr2', 'libxrender1',
	# 		'libxss1', 'libxtst6', 'libnss3'],

	sudo DEBIAN_FRONTEND=noninteractive apt-get install build-essential -yqqq
	sudo DEBIAN_FRONTEND=noninteractive apt-get install locales -yqqq
	sudo DEBIAN_FRONTEND=noninteractive apt-get install git -yqqq
	sudo DEBIAN_FRONTEND=noninteractive apt-get install libfontconfig -yqqq
	sudo DEBIAN_FRONTEND=noninteractive apt-get install wget -yqqq
	sudo DEBIAN_FRONTEND=noninteractive apt-get install htop -yqqq
	sudo DEBIAN_FRONTEND=noninteractive apt-get install libxml2 -yqqq
	sudo DEBIAN_FRONTEND=noninteractive apt-get install libxslt1-dev -yqqq
	sudo DEBIAN_FRONTEND=noninteractive apt-get install python3-dev -yqqq
	sudo DEBIAN_FRONTEND=noninteractive apt-get install python3-dbg -yqqq
	sudo DEBIAN_FRONTEND=noninteractive apt-get install python3-distutils -yqqq
	sudo DEBIAN_FRONTEND=noninteractive apt-get install libz-dev -yqqq
	sudo DEBIAN_FRONTEND=noninteractive apt-get install curl -yqqq
	sudo DEBIAN_FRONTEND=noninteractive apt-get install screen -yqqq
	sudo DEBIAN_FRONTEND=noninteractive apt-get install libasound2 -yqqq
	sudo DEBIAN_FRONTEND=noninteractive apt-get install libatk1.0-0 -yqqq
	sudo DEBIAN_FRONTEND=noninteractive apt-get install libc6 -yqqq
	sudo DEBIAN_FRONTEND=noninteractive apt-get install libcairo2 -yqqq
	sudo DEBIAN_FRONTEND=noninteractive apt-get install libcups2 -yqqq
	sudo DEBIAN_FRONTEND=noninteractive apt-get install libdbus-1-3 -yqqq
	sudo DEBIAN_FRONTEND=noninteractive apt-get install libexpat1 -yqqq
	sudo DEBIAN_FRONTEND=noninteractive apt-get install libfontconfig1 -yqqq
	sudo DEBIAN_FRONTEND=noninteractive apt-get install libgcc1 -yqqq
	sudo DEBIAN_FRONTEND=noninteractive apt-get install libgconf-2-4 -yqqq
	sudo DEBIAN_FRONTEND=noninteractive apt-get install libgdk-pixbuf2.0-0 -yqqq
	sudo DEBIAN_FRONTEND=noninteractive apt-get install libglib2.0-0 -yqqq
	sudo DEBIAN_FRONTEND=noninteractive apt-get install libgtk-3-0 -yqqq
	sudo DEBIAN_FRONTEND=noninteractive apt-get install libnspr4 -yqqq
	sudo DEBIAN_FRONTEND=noninteractive apt-get install libpango-1.0-0 -yqqq
	sudo DEBIAN_FRONTEND=noninteractive apt-get install libpangocairo-1.0-0 -yqqq
	sudo DEBIAN_FRONTEND=noninteractive apt-get install libstdc++6 -yqqq
	sudo DEBIAN_FRONTEND=noninteractive apt-get install libx11-6 -yqqq
	sudo DEBIAN_FRONTEND=noninteractive apt-get install libx11-xcb1 -yqqq
	sudo DEBIAN_FRONTEND=noninteractive apt-get install libxcb1 -yqqq
	sudo DEBIAN_FRONTEND=noninteractive apt-get install libxcursor1 -yqqq
	sudo DEBIAN_FRONTEND=noninteractive apt-get install libxdamage1 -yqqq
	sudo DEBIAN_FRONTEND=noninteractive apt-get install libxext6 -yqqq
	sudo DEBIAN_FRONTEND=noninteractive apt-get install libxfixes3 -yqqq
	sudo DEBIAN_FRONTEND=noninteractive apt-get install libxi6 -yqqq
	sudo DEBIAN_FRONTEND=noninteractive apt-get install libxrandr2 -yqqq
	sudo DEBIAN_FRONTEND=noninteractive apt-get install libxrender1 -yqqq
	sudo DEBIAN_FRONTEND=noninteractive apt-get install libxss1 -yqqq
	sudo DEBIAN_FRONTEND=noninteractive apt-get install libxtst6 -yqqq
	sudo DEBIAN_FRONTEND=noninteractive apt-get install libnss3 -yqqq
	sudo DEBIAN_FRONTEND=noninteractive apt-get install xvfb -yqqq

	# Adblocking. Lower the chrome cpu costs decently
	# So long hosts files cause things to explode, so we turn it off.
	# ['cmd.run', ["curl https://raw.githubusercontent.com/StevenBlack/hosts/master/alternates/social/hosts | tee -a /etc/hosts


	# Needed to make GCE play nice. I think they just flat-out don't preinstall a locale
	# ['cmd.run', ["sudo apt-get install language-pack-en -y", ],                                                                           {}, ['The following NEW packages will be installed:', 'language-pack-en-base']],

	# Shit to make the tty work in UTF-8. Otherwise, the logging can asplode
	# and break all the things.
	echo LANG=\"en_US.UTF-8\"   >> /etc/default/locale
	echo LC_ALL=\"en_US.UTF-8\" >> /etc/default/locale
	echo "LC_ALL=en_US.UTF-8"   >> /etc/environment
	echo "en_US.UTF-8 UTF-8"    >> /etc/locale.gen
	echo "LANG=en_US.UTF-8"     > /etc/locale.conf
	dpkg-reconfigure -f noninteractive locales | grep -q 'en_US.UTF-8'
	locale
	bash -c \"locale\"


	# Clone and Install settings
	ls / | grep -q 'scraper'
	git clone https://github.com/fake-name/AutoTriever.git /scraper

			# Make sure it all checked out at least somewhat
	ls /scraper  | grep -q 'configure.sh'
	ls /scraper  | grep -q 'run.sh'
	ls /scraper  | grep -q 'settings.json'

	# Finally, run the thing

	adduser scrapeworker --disabled-password --gecos ""
	usermod -a -G sudo scrapeworker
	echo 'scrapeworker ALL=(ALL) NOPASSWD: ALL' | tee -a /etc/sudoers

	wget https://raw.githubusercontent.com/solarkennedy/instant-py-bt/master/py-bt -O /usr/local/bin/py-bt
	wget https://raw.githubusercontent.com/aurora/rmate/master/rmate -O /usr/local/bin/rmate
	chmod +x /usr/local/bin/py-bt
	chmod +x /usr/local/bin/rmate

	chown -R scrapeworker:scrapeworker /scraper
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
		sudo DEBIAN_FRONTEND=noninteractive apt-get install libgconf-2-4 -yqqq

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
		sudo DEBIAN_FRONTEND=noninteractive apt-get install libgconf-2-4 -yqqq

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

	# Fix perms (if the setup was run as root, .git will be inaccessible)
	sudo chown -R scrapeworker:scrapeworker /scraper

	echo "Setup OK! System is configured for launch"

}


# Snapd is flaming garbage, and should never be installed on anything
function block_snapd() {
	echo "Package: snapd" | sudo tee -a /etc/apt/preferences.d/block-snap
	echo "Pin: release *" | sudo tee -a /etc/apt/preferences.d/block-snap
	echo "Pin-Priority: -1" | sudo tee -a /etc/apt/preferences.d/block-snap
}


function install_start_unit_file() {

	if [ ! -f /etc/systemd/system/rwpscraper.service ]; then

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
	else
		echo "Do not need to install unit file, as it already exists"
	fi

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
	check_install_swap

	if [ "$is_local" = true ] ; then
		go_local_install
		chrome_postinstall_local
	else
		do_remote_install
		chrome_postinstall_remote
		install_start_unit_file

	fi

	echo "Setup OK! System is configured for launch"

}


go "$@"

