

import queue
import time
import threading
import traceback
import concurrent.futures
import json
import logging
import os.path
import os

import deps.logSetup
import dispatcher

import state



class SettingsLoadFailed(ValueError):
	pass

def loadSettings():

	settings = None

	sPaths = ['./settings.json', '../settings.json']

	for sPath in sPaths:
		if not os.path.exists(sPath):
			continue
		with open('./settings.json', 'r') as fp:
			print("Found settings.json file! Loading settings.")
			settings = json.load(fp)

	if not settings and 'SCRAPE_CREDS' in os.environ:
		print("Found 'SCRAPE_CREDS' environment variable! Loading settings.")
		settings = json.loads(os.environ['SCRAPE_CREDS'])

	if not settings:
		raise SettingsLoadFailed("No settings.json file or 'SCRAPE_CREDS' environment variable found!")

	return settings


def launchThread(settings, lock_dict):
	rpc = None
	while 1:
		try:
			if not rpc:
				rpc = dispatcher.RpcCallDispatcher(settings, lock_dict)
			rpc.processEvents()
		except KeyboardInterrupt:
			break
		except Exception:
			print("Error! Wat?")
			traceback.print_exc()
			rpc = None
			time.sleep(60*3)

def multithread(numThreads, settings, lock_dict):

	print("Launching {num} threads.".format(num=numThreads))

	with concurrent.futures.ThreadPoolExecutor(max_workers=numThreads) as executor:
		for thnum in range(numThreads):
			print("Launching thread {num}".format(num=thnum))
			executor.submit(launchThread, settings, lock_dict)
		try:
			while 1:
				time.sleep(1)
		except KeyboardInterrupt:
			print("Main thread interrupt!")
			state.RUN_STATE = False

	print("Main thread exited.")


def go():
	print("AutoTreiver Launching!")
	deps.logSetup.initLogging(logLevel=logging.INFO)
	settings = loadSettings()



	threads = 1
	if 'threads' in settings and settings['threads']:
		threads = settings['threads']
		print("Have multithreading configuration directive!", threads)
	else:
		print("Running in single thread mode.")

	settings['aux_message_queue'] = queue.Queue()
	manager_lock   = threading.Lock()
	seen_lock      = threading.Lock()
	serialize_lock = threading.Lock()

	lock_dict = {
		'manager_lock'   : manager_lock,
		'seen_lock'      : seen_lock,
		'serialize_lock' : serialize_lock,
		}

	if threads == 1:
		launchThread(settings, lock_dict)
	else:
		multithread(threads, settings, lock_dict)

if __name__ == "__main__":
	go()
