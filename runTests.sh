#!/bin/bash


# python3 -m unittest Tests.DbContentTests

# coverage run --source=./dbApi.py -m unittest Tests.DbApiTests

# Coverage doesn't work with cython files.
# Therefore, we don't run the BK Tree tests with it.
# python3 -m unittest Tests.BinaryConverterTests
# python3 -m unittest Tests.BKTreeTests
# python3 -m unittest Tests.Test_BKTree_Concurrency


# Test ALL THE THINGS

set -e

nosetests                       \
	--with-coverage                              \
	--exe                                        \
	--cover-package=util.WebRequest             \
	--stop
	# --nocapture

coverage report --show-missing

coverage erase

