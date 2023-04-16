#!/usr/bin/env bash

# Halt on errors.
# set -e

alembic upgrade head


set +e


if [ -f "local_configured" ]
then
	echo "Config indicator file exists. Skipping setup!"
else
	echo "Config indicator file is missing! Doing setup!"
	# Run the configure script
	bash ./configure.sh include_submodule
fi;


until python3 ./main_scheduled.py; do
    echo "Server 'python3 ./main_scheduled.py' crashed with exit code $?.  Respawning.." >&2
    killall -r "python3"
    killall -9 chrome
    sleep 30
done
