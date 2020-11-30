#!/usr/bin/env bash

# Halt on errors.
set -e

alembic upgrade head

python3 ./main_scheduled.py
