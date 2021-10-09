#!/bin/bash

if ((EUID != 0)); then
    echo "Root or Sudo  Required for script ( $(basename $0) )"
    exit
fi


until python3 ./salt_scheduler.py; do
	echo "Server 'python3 ./salt_scheduler.py' crashed with exit code $?.  Respawning.." >&2
	killall -r "python3"
	sleep 30
done

