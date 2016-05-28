

import dispatcher
import time
import traceback
import concurrent.futures
import json
import deps.logSetup
import logging
import os.path
import os


RUN_STATE = True


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
		raise ValueError("No settings.json file or 'SCRAPE_CREDS' environment variable found!")

	return settings


def launchThread(settings):
	print("Launching scraper in single-threaded mode.")
	rpc = None
	while 1:
		try:
			if not rpc:
				rpc = dispatcher.RpcCallDispatcher(settings)
			rpc.processEvents()
		except KeyboardInterrupt:
			break
		except Exception:
			print("Error! Wat?")
			traceback.print_exc()
			rpc = None
			time.sleep(60*3)

def multithread(numThreads, settings):
	global RUN_STATE

	print("Launching {num} threads.".format(num=numThreads))

	with concurrent.futures.ThreadPoolExecutor(max_workers=numThreads) as executor:
		for thnum in range(numThreads):
			print("Launching thread {num}".format(num=thnum))
			executor.submit(launchThread, settings)
		try:
			while 1:
				time.sleep(1)
		except KeyboardInterrupt:
			print("Main thread interrupt!")

		RUN_STATE = False

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



	if threads == 1:
		launchThread(settings)
	else:
		multithread(threads, settings)

if __name__ == "__main__":
	go()
