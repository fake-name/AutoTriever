

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
from autotriever import main_entry_point

from scheduled import scheduler

def go():
	autotriever.deps.logSetup.initLogging(logLevel=logging.INFO)

	scheduler.run_scheduler_thread()
	main_entry_point.go()


if __name__ == "__main__":
	go()
