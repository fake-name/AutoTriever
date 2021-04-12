#!/usr/bin/env bash

# Halt on errors.
# set -e

alembic upgrade head


set +e


until python3 ./main_scheduled.py; do
    echo "Server 'python3 ./main_scheduled.py' crashed with exit code $?.  Respawning.." >&2
    killall -r "python3"
    killall -9 chrome
    sleep 30
done
