#!/usr/bin/env python3
import AmqpConnector
import msgpack
import logging
import os.path
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
		assert 'clientid'     in settings
		assert "RABBIT_LOGIN" in settings
		assert "RABBIT_PASWD" in settings
		assert "RABBIT_SRVER" in settings
		assert "RPC_RABBIT_VHOST" in settings

		if not self.settings:
			raise ValueError("The 'settings.json' file was not found!")

		self.cert = self.findCert()



	def findCert(self):
		'''
		Verify the SSL cert exists in the proper place.
		'''

		curFile = os.path.abspath(__file__)

		curDir = os.path.split(curFile)[0]
		caCert = os.path.abspath(os.path.join(curDir, './deps/cacert.pem'))
		cert = os.path.abspath(os.path.join(curDir, './deps/cert.pem'))
		keyf = os.path.abspath(os.path.join(curDir, './deps/key.pem'))

		assert os.path.exists(caCert), "No certificates found on path '%s'" % caCert
		assert os.path.exists(cert), "No certificates found on path '%s'" % cert
		assert os.path.exists(keyf), "No certificates found on path '%s'" % keyf


		return {"cert_reqs" : ssl.CERT_REQUIRED,
				"ca_certs" : caCert,
				"keyfile"  : keyf,
				"certfile"  : cert,
			}



	def process(self, body):
		raise ValueError("This must be subclassed!")


	def _process(self, body):
		# body = json.loads(body)
		body = msgpack.unpackb(body, use_list=True, encoding='utf-8')

		assert isinstance(body, dict) == True, 'The message must decode to a dict!'

		delay = None

		try:
			if 'postDelay' in body:
				delay = int(body['postDelay'])

			self.log.info("Received request. Processing.")
			ret = self.process(body)

			assert isinstance(ret, dict) == True, '`process()` call in child-class must return a dict!'

			# Copy the jobid and dbid across, so we can cross-reference the job
			# when it's received.
			if 'jobid' in body:
				ret['jobid'] = body['jobid']

			if not 'success' in ret:
				ret['success'] = True
			if not 'cancontinue' in ret:
				ret['cancontinue'] = True


			self.log.info("Processing complete. Submitting job with id '%s'.", ret['jobid'])
		except Exception:
			ret = {
				'success'     : False,
				'error'       : "unknown",
				'traceback'   : traceback.format_exc(),
				'cancontinue' : True
			}
			if 'jobid' in body:
				ret['jobid'] = body['jobid']

			self.log.error("Had exception?")
			for line in traceback.format_exc().split("\n"):
				self.log.error(line)


			# Disable the delay if the call had an exception.
			delay = 0

		if not 'cancontinue' in ret:
			self.log.error('Invalid return value from `process()`')
		elif not ret['cancontinue']:
			self.log.error('Uncaught error in `process()`. Exiting.')
			self.die = True


		ret['user'] = self.settings['clientid']

		self.log.info("Returning")

		return msgpack.packb(ret, use_bin_type=True), delay
		# return json.dumps(ret), delay

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

		sslopts = self.findCert()
		connector = None
		try:
			while RUN_STATE and not self.die:
				try:
					if not connector:
						self.log.info("Initializing AMQP Connection!")
						connector = AmqpConnector.Connector(userid              = self.settings["RABBIT_LOGIN"],
															password            = self.settings["RABBIT_PASWD"],
															host                = self.settings["RABBIT_SRVER"],
															virtual_host        = self.settings["RPC_RABBIT_VHOST"],
															ssl                 = sslopts,
															task_exchange_type = "direct",
															# session_fetch_limit = 1,
															durable             = True,
															)
						self.log.info("AMQP Connection initialized. Entering runloop!")
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
						self.log.info("Processing message.")

						response, postDelay = self._process(message)

						self.log.info("Response message size: %0.3fK. Sending", len(response)/1024.0)
						connector.putMessage(response)
						break

					time.sleep(0.1)

				# self.log.info("Closing RPC queue connection.")
				# connector.stop()


				self.successDelay(postDelay)


		except KeyboardInterrupt:
			self.log.info("Keyboard Interrupt exit!")
			self.die = True


		self.log.info("Halting message consumer.")
		try:
			connector.stop()
		except Exception:
			self.log.error("Closing the connector produced an error!")
			for line in traceback.format_exc().split("\n"):
				self.log.error(line)


		self.log.info("Closed. Exiting")

		if not RUN_STATE or self.die:
			raise KeyboardInterrupt
