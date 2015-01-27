

import dispatcher
import time
import concurrent.futures
import deps.webFunctions
import json
import deps.logSetup
import logging
import os.path

RUN_STATE = True


def loadSettings():

	settings = None

	sPaths = ['./settings.json', '../settings.json']

	for sPath in sPaths:
		if not os.path.exists(sPath):
			continue
		with open('./settings.json', 'r') as fp:
			settings = json.load(fp)

	if not settings:
		raise ValueError("No settings.json file found!")

	return settings


def launchThread(settings):
	print("Launching scraper in single-threaded mode.")
	rpc = dispatcher.RpcCallDispatcher(settings)
	rpc.processEvents()

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
