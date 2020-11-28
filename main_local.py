

import queue
import time
import threading
import traceback
import concurrent.futures
import json
import logging
import os.path
import os

import autotriever.deps.logSetup
from autotriever import local_entry_point


def go():
	autotriever.deps.logSetup.initLogging(logLevel=logging.INFO)
	local_entry_point.go()


if __name__ == "__main__":
	go()
