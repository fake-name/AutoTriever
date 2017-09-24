
#!/usr/bin/env python3
import logging
import uuid
import os.path
import threading
import ssl
import time
import traceback
import msgpack
import amqp_connector
from state import RUN_STATE

# CHUNK_SIZE_BYTES = 250 * 1024
CHUNK_SIZE_BYTES = 100 * 1024

def chunk_input(inval, chunk_size):
	for i in range(0, len(inval), chunk_size):
		yield inval[i:i+chunk_size]

class SeenMessageError(Exception):
	pass

INSTANCE_SEEN_MESSAGE_IDS = set()

class RpcHandler(object):
	die = False

	def __init__(self, settings, seen_lock, serialize_lock):

		thName = threading.current_thread().name
		if "-" in thName:
			logPath = "Main.Thread-{num}.RPC".format(num=thName.split("-")[-1])
		else:
			logPath = 'Main.RPC'

		self.log = logging.getLogger(logPath)
		self.log.info("RPC Management class instantiated.")

		self.seen_lock      = seen_lock
		self.serialize_lock = serialize_lock
		self.settings       = settings

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



	def process(self, body, context_responder):
		raise ValueError("This must be subclassed!")

	def partial_response(self, context, connector):
		# Hurray for closure abuse.
		def partial_capture(logs, content):
			assert isinstance(content, dict), '`partial response` must be passed a dict!'
			self.log.info("Doing incremental response transmission")
			response = {
				'ret'          : (logs, content),
				'success'      : True,
				'cancontinue'  : True,
				'partial'      : True,
				'dispatch_key' : context['dispatch_key'],
				'module'       : context['module'],
				'call'         : context['call'],
				'user'         : self.settings['clientid'],
				'user_uuid'    : self.settings['client_key'],
			}

			# Copy the jobid and dbid across, so we can cross-reference the job
			# when it's received.
			if 'jobid' in context:
				response['jobid'] = context['jobid']
			if 'jobmeta' in context:
				response['jobmeta'] = context['jobmeta']
			if 'extradat' in context:
				response['extradat'] = context['extradat']

			self.put_message_chunked(response, connector)

		return partial_capture


	def _process(self, body_r, connector):
		# body = json.loads(body)
		body = msgpack.unpackb(body_r, use_list=True, encoding='utf-8')

		assert isinstance(body, dict) is True, 'The message must decode to a dict!'

		if "unique_id" in body:
			with self.seen_lock:
				mid = body['unique_id']
				if mid in INSTANCE_SEEN_MESSAGE_IDS:
					self.log.info("Seen unique message ID: %s. Not fetching again", mid)
					raise SeenMessageError
				else:
					self.log.info("New unique message ID: %s. Fetching.", mid)
					INSTANCE_SEEN_MESSAGE_IDS.add(mid)

		have_serialize_lock = False
		if 'serialize' in body and body['serialize']:
			acquired = self.serialize_lock.acquire(blocking=False)
			if not acquired:
				self.log.info("Forcing job to be serialized on worker. Rejecting while a job is active.")
				raise SeenMessageError
			have_serialize_lock = True


		delay = None

		try:
			if 'postDelay' in body:
				delay = int(body['postDelay'])

			self.log.info("Received request. Processing.")
			ret = self.process(body, self.partial_response(body, connector))

			assert isinstance(ret, dict), '`process()` call in child-class must return a dict!'

			ret.setdefault('success', True)
			ret.setdefault('cancontinue', True)


			self.log.info("Processing complete. Submitting job with id '%s'.", body['jobid'])
		except Exception as e:

			if "unique_id" in body:
				with self.seen_lock:
					INSTANCE_SEEN_MESSAGE_IDS.discard(body['unique_id'])

			ret = {
				'success'     : False,
				'error'       : "unknown",
				'traceback'   : traceback.format_exc().split("\n"),
				'cancontinue' : True
			}
			if hasattr(e, 'log_data'):
				ret['log'] = e.log_data

			self.log.error("Had exception?")
			for line in traceback.format_exc().split("\n"):
				self.log.error(line)


			# Disable the delay if the call had an exception.
			delay = 0

		if 'cancontinue' not in ret:
			self.log.error('Invalid return value from `process()`')
		elif not ret['cancontinue']:
			self.log.error('Uncaught error in `process()`. Exiting.')
			self.die = True


		ret['user'] = self.settings['clientid']
		ret['user_uuid'] = self.settings['client_key']


		# Copy the jobid and dbid across, so we can cross-reference the job
		# when it's received.
		if 'jobid' in body:
			ret['jobid'] = body['jobid']
		if 'jobmeta' in body:
			ret['jobmeta'] = body['jobmeta']
		if 'extradat' in body:
			ret['extradat'] = body['extradat']

		# Main return path isn't a partial
		ret.setdefault('partial', False)
		self.log.info("Returning")

		if have_serialize_lock:
			self.serialize_lock.release()

		return ret, delay

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

	def put_message_chunked(self, message, connector):

		message_bytes = msgpack.packb(message, use_bin_type=True)
		if len(message_bytes) < CHUNK_SIZE_BYTES:

			message = {
				'chunk-type'         : "complete-message",
				'data'         : message,
			}
			bmessage = msgpack.packb(message, use_bin_type=True)

			self.log.info("Response message size: %0.3fK. Sending", len(bmessage)/1024.0)
			connector.put_response(bmessage)
		else:
			chunked_id = "chunk-merge-key-"+uuid.uuid4().hex
			chunkl = list(enumerate(chunk_input(message_bytes, CHUNK_SIZE_BYTES)))
			for idx, chunk in chunkl:
				message = {
					'chunk-type'   : "chunked-message",
					'chunk-num'    : idx,
					'total-chunks' : len(chunkl),
					'data'         : chunk,
					'merge-key'    : chunked_id,
				}
				bmessage = msgpack.packb(message, use_bin_type=True)
				self.log.info("Response chunk message size: %0.3fK. Sending", len(bmessage)/1024.0)
				connector.put_response(bmessage)



	def process_messages(self, connector_instance, loops):

		msg_count = 0
		for message in connector_instance.get_iterator():
			if not RUN_STATE or self.die:
				return

			if message:
				msg_count += 1
				self.log.info("Processing message. (%s of %s before connection reset)", msg_count, loops)

				try:
					response, postDelay = self._process(message.body, connector_instance)

					self.put_message_chunked(response, connector_instance)
					# connector_instance.put_response(response)

					# Ack /after/ we've done the task.
					message.ack()

					self.successDelay(postDelay)
				except SeenMessageError:
					self.log.warning("Message has uniqueID that has been seen. Returning to processing queue")
					# Push into dead-letter queue.
					message.reject(requeue=False)
					time.sleep(1)

			if msg_count > loops:
				return
	def processEvents(self):
		'''
		Connect to the server, wait for a task, and then disconnect untill another job is
		received.

		The AMQP connection is not maintained due to issues with long-lived connections.

		'''

		sslopts = self.findCert()
		connector_instance = None
		try:
			while RUN_STATE and not self.die:
				try:
					self.log.info("Initializing AMQP Connection!")
					connector_instance = amqp_connector.Connector(userid              = self.settings["RABBIT_LOGIN"],
										password            = self.settings["RABBIT_PASWD"],
										host                = self.settings["RABBIT_SRVER"],
										virtual_host        = self.settings["RPC_RABBIT_VHOST"],
										ssl                 = sslopts,
										prefetch            = 2,
										synchronous         = True,
										task_exchange_type  = "direct",
										durable             = True,
									)

					self.log.info("AMQP Connection initialized. Entering runloop!")

					self.process_messages(connector_instance, 100)
					connector_instance.close()
					connector_instance = None

				except IOError:
					self.log.error("Error while connecting to server.")
					self.log.error("Is the AMQP server not available?")
					for line in traceback.format_exc().split("\n"):
						self.log.error(line)
					self.log.error("Trying again in 30 seconds.")
					time.sleep(30)
					continue

				self.log.info("Connection Established. Awaiting RPC requests")

		except KeyboardInterrupt:
			self.log.info("Keyboard Interrupt exit!")
			self.die = True


		self.log.info("Halting message consumer.")
		try:
			connector_instance.close()
		except Exception:
			self.log.error("Closing the connector produced an error!")
			for line in traceback.format_exc().split("\n"):
				self.log.error(line)


		self.log.info("Closed. Exiting")

		if not RUN_STATE or self.die:
			raise KeyboardInterrupt
