#!/usr/bin/env python3
import AmqpConnector
import concurrent.futures
import deps.webFunctions
import json
import logging
import os.path
import deps.logSetup
import threading
import ssl
import time
import traceback

RUN_STATE = True

class RpcHandler(object):
	die = False

	def __init__(self, settings):

		thName = threading.current_thread().name
		if "-" in thName:
			logPath = "Main.Thread-{num}.RPC".format(num=thName.split("-")[-1])
		else:
			logPath = 'Main.RPC'

		self.log = logging.getLogger(logPath)
		self.log.info("RPC Management class instantiated.")

		self.settings = settings

		# Require clientID in settings
		assert 'clientid' in settings
		assert "RABBIT_LOGIN" in settings
		assert "RABBIT_PASWD" in settings
		assert "RABBIT_SRVER" in settings
		assert "RABBIT_VHOST" in settings

		if not self.settings:
			raise ValueError("The 'settings.json' file was not found!")

		self.cert = self.findCert()



	def findCert(self):
		'''
		Verify the SSL cert exists in the proper place.
		'''
		curFile = os.path.abspath(__file__)

		curDir = os.path.split(curFile)[0]
		certPath = os.path.join(curDir, './deps/cacert.pem')

		assert os.path.exists(certPath)

		return certPath



	def process(self, body):
		raise ValueError("This must be subclassed!")


	def _process(self, body):
		body = json.loads(body)
		delay = None

		try:
			if 'postDelay' in body:
				delay = int(body['postDelay'])

			self.log.info("Received request. Processing.")
			ret = self.process(body)


			# Copy the jobid and dbid across, so we can cross-reference the job
			# when it's received.
			if 'dbId' in body:
				ret['dbid']  = body['dbid']
			if 'jobid' in body:
				ret['jobid'] = body['jobid']

			if not 'success' in ret:
				ret['success'] == True

			self.log.info("Processing complete. Submitting job with id '%s'.", ret['jobid'])
		except Exception:
			ret = {
				'success'     : False,
				'error'       : "unknown",
				'traceback'   : traceback.format_exc(),
				'cancontinue' : False
			}
			self.log.error("Had exception?")
			for line in traceback.format_exc().split("\n"):
				self.log.error(line)

		if not 'cancontinue' in ret:
			self.log.error('Invalid return value from `process()`')
		elif not ret['cancontinue']:
			self.log.error('Uncaught error in `process()`. Exiting.')
			self.die = True



		ret['user'] = self.settings['clientid']

		self.log.info("Returning")

		return json.dumps(ret), delay

	def successDelay(self, sleeptime):
		'''
		Delay for `sleeptime` seconds, but output a "Oh hai, I'm sleeping" message
		every 15 seconds while doing so.
		Also, return immediately if told to exit.
		'''
		if sleeptime and not self.die and RUN_STATE:

			self.log.info("Sleeping %s seconds.", sleeptime)

			for x in range(sleeptime):
				time.sleep(1)
				if (sleeptime - x) % 15 == 0:
					self.log.info("Sleeping %s more seconds....", sleeptime - x)
				if not RUN_STATE:
					self.log.info( "Breaking due to exit flag being set")
					break



	def processEvents(self):
		'''
		Connect to the server, wait for a task, and then disconnect untill another job is
		received.

		The AMQP connection is not maintained due to issues with long-lived connections.

		'''

		if self.cert:
			sslopts = {"cert_reqs" : ssl.CERT_REQUIRED, "ca_certs" : self.cert}
		else:
			sslopts = None

		try:
			while RUN_STATE and not self.die:
				try:
					connector = AmqpConnector.Connector(userid      = self.settings["RABBIT_LOGIN"],
															password     = self.settings["RABBIT_PASWD"],
															host         = self.settings["RABBIT_SRVER"],
															virtual_host = self.settings["RABBIT_VHOST"],
															ssl          = sslopts)
				except IOError:
					self.log.error("Error while connecting to server.")
					self.log.error("Is the AMQP server not available?")
					for line in traceback.format_exc().split("\n"):
						self.log.error(line)
					self.log.error("Trying again in 30 seconds.")
					time.sleep(30)
					continue

				self.log.info("Connection Established. Awaiting RPC requests")


				while RUN_STATE and not self.die:
					message = connector.getMessage()
					if message:

						response, postDelay = self._process(message)

						self.log.info("Response message size: %0.3fK. Sending", int(len(response)/1024))
						connector.putMessage(response)
						break

					time.sleep(0.1)

				self.log.info("Closing RPC queue connection.")
				connector.stop()


				self.successDelay(postDelay)


		except KeyboardInterrupt:
			self.log.info("Keyboard Interrupt exit!")

		self.log.info("Halting message consumer.")
		try:
			connector.stop()
		except Exception:
			self.log.error("Closing the connector produced an error!")
			for line in traceback.format_exc().split("\n"):
				self.log.error(line)


		self.log.info("Closed. Exiting")

class Grabber(RpcHandler):

	def __init__(self, settings):
		super().__init__(settings)

		self.wg = deps.webFunctions.WebGetRobust()

	def process(self, body):
		print("STUFF GOES HERE")

		# import string
		# size = random.randint(1, 100)
		# fCont = ''.join(random.choice(string.printable) for i in range(1024*32))
		# fCont = fCont * 32 * size
		# fCont = bytes(fCont, 'ascii')

		# fName = u'datTemp-{num}.bin'.format(num=time.time())

		# ret = {
		# 	u'success'     : True,
		# 	u'fileN'       : fName,
		# 	u'fileC'       : 'wat',
		# 	u'cancontinue' : True
		# }


		# return ret

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
	rpc = Grabber(settings)
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
