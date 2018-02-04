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
		yield inval[i:i + chunk_size]


class CannotHandleNow(Exception):
	pass


INSTANCE_SEEN_MESSAGE_IDS = set()


def forward_attachments(context, response):
	# Copy the jobid and dbid across, so we can cross-reference the job
	# when it's received.
	if 'jobid' in context:
		response['jobid'] = context['jobid']
	if 'jobmeta' in context:
		response['jobmeta'] = context['jobmeta']
	if 'extradat' in context:
		response['extradat'] = context['extradat']

	return response


def findCert():
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

	return {
					"cert_reqs": ssl.CERT_REQUIRED,
					"ca_certs": caCert,
					"keyfile": keyf,
					"certfile": cert,
	}


class RpcHandler(object):
	die = False

	def __init__(self, settings, lock_dict):

		thName = threading.current_thread().name
		if "-" in thName:
			logPath = "Main.Thread-{num}.RPC".format(num=thName.split("-")[-1])
		else:
			logPath = 'Main.RPC'

		self.log = logging.getLogger(logPath)
		self.log.info("RPC Management class instantiated.")

		self.lock_dict = lock_dict
		# self.seen_lock = seen_lock
		# self.serialize_lock = serialize_lock
		self.settings = settings

		if settings:
			# Require clientID in settings
			assert 'clientid' in settings
			assert "RABBIT_LOGIN" in settings
			assert "RABBIT_PASWD" in settings
			assert "RABBIT_SRVER" in settings
			assert "RPC_RABBIT_VHOST" in settings


			if not self.settings:
				raise ValueError("The 'settings.json' file was not found!")

		else:
			self.log.warning("Settings is NULL")
			self.log.warning("Assuming running in test mode!")


		self.connector = None

	def process(self, body, context_responder):  # pylint: disable=unused-argument
		raise ValueError("This must be subclassed!")

	def capture_partial_response(self, context, response_routing_key=None):
		# Hurray for closure abuse.
		def partial_capture(logs, content):
			assert isinstance(content, dict), '`partial response` must be passed a dict!'
			self.log.info("Doing incremental response transmission")
			response = {
							'ret': (logs, content),
							'success': True,
							'cancontinue': True,
							'partial': True,
							'dispatch_key': context['dispatch_key'],
							'module': context['module'],
							'call': context['call'],
							'user': self.settings['clientid'],
							'user_uuid': self.settings['client_key'],
			}

			response = forward_attachments(context, response)

			self.put_message_chunked(response, routing_key_override=response_routing_key)

		return partial_capture

	def _call_dispatcher(self, body, response_routing_key):

		# Delay is zero, unless overridden
		delay = 0

		try:

			delay = int(body.get('postDelay', 0))

			self.log.info("Received request. Processing.")
			captured_partial = self.capture_partial_response(body, response_routing_key)
			response = self.process(body, captured_partial)

			assert isinstance(response, dict), '`process()` call in child-class must return a dict!'

			response.setdefault('success', True)
			response.setdefault('cancontinue', True)

			self.log.info("Processing complete. Submitting job with id '%s'.", body['jobid'])

		except Exception as exc:
			if "unique_id" in body:
				with self.lock_dict['seen_lock']:
					INSTANCE_SEEN_MESSAGE_IDS.discard(body['unique_id'])

			response = {
							'success': False,
							'error': "unknown",
							'traceback': traceback.format_exc().split("\n"),
							'cancontinue': True
			}

			if hasattr(exc, 'log_data'):
				response['log'] = exc.log_data

			self.log.error("Had exception?")
			for line in traceback.format_exc().split("\n"):
				self.log.error(line)

		return response, delay

	def _dispatch_binary_message(self, message):
		# body = json.loads(body)

		have_serialize_lock = False
		early_acked = False
		try:

			body = msgpack.unpackb(message.body, use_list=True, encoding='utf-8')

			assert isinstance(body, dict) is True, 'The message must decode to a dict!'


			if "unique_id" in body:
				with self.lock_dict['seen_lock']:
					mid = body['unique_id']
					if mid in INSTANCE_SEEN_MESSAGE_IDS:
						self.log.warning("Seen unique message ID: %s (have %s seen items). Not fetching again", mid,
																							len(INSTANCE_SEEN_MESSAGE_IDS))
						raise CannotHandleNow
					else:
						self.log.info("New unique message ID: %s. Fetching.", mid)
						INSTANCE_SEEN_MESSAGE_IDS.add(mid)

			if 'serialize' in body and body['serialize']:
				lockname = body['serialize'] if isinstance(body['serialize'], str) else 'generic_job'

				# Don't allow the serialization interface to acquire locks for
				# other things.
				assert lockname not in ['manager_lock', 'seen_lock']

				# If the lock is new, insert it into the lock
				# dict in a thread-safe manner
				if not lockname in self.lock_dict:
					with self.lock_dict['manager_lock']:
						if not lockname in self.lock_dict:
							self.lock_dict[lockname] = threading.Lock()

				have_serialize_lock = self.lock_dict[lockname].acquire(blocking=False)
				if not have_serialize_lock:
					self.log.warning("Forcing job to be serialized on worker (lock: %s). Rejecting while another job is active.", lockname)
					raise CannotHandleNow

			if "early_ack" in body and body['early_ack']:
				message.ack()
				early_acked = True

			response_routing_key = body.get('response_routing_key', None)

			response, delay = self._call_dispatcher(body, response_routing_key)

			if 'cancontinue' not in response:
				self.log.error('Invalid return value from `process()`')

			elif not response['cancontinue']:
				self.log.error('Uncaught error in `process()`. Exiting.')
				self.die = True

			response['user'] = self.settings['clientid']
			response['user_uuid'] = self.settings['client_key']

			# Main return path isn't a partial
			response.setdefault('partial', False)
			self.log.info("Returning")

			response = forward_attachments(body, response)

			return early_acked, response, delay, response_routing_key
		finally:
			if have_serialize_lock:
				self.log.info("Releasing serialization lock.")
				self.lock_dict[lockname].release()

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
					self.log.info("Breaking due to exit flag being set")
					break

	def put_message_chunked(self, message, routing_key_override=None):

		message_bytes = msgpack.packb(message, use_bin_type=True)
		if len(message_bytes) < CHUNK_SIZE_BYTES:

			message = {
							'chunk-type': "complete-message",
							'data': message,
			}
			bmessage = msgpack.packb(message, use_bin_type=True)

			self.log.info("Response message size: %0.3fK. Sending with routing key %s", len(bmessage) / 1024.0, routing_key_override)
			self.connector.put_response(bmessage, routing_key_override=routing_key_override)
		else:
			chunked_id = "chunk-merge-key-" + uuid.uuid4().hex
			chunkl = list(enumerate(chunk_input(message_bytes, CHUNK_SIZE_BYTES)))
			for idx, chunk in chunkl:
				message = {
								'chunk-type': "chunked-message",
								'chunk-num': idx,
								'total-chunks': len(chunkl),
								'data': chunk,
								'merge-key': chunked_id,
				}
				bmessage = msgpack.packb(message, use_bin_type=True)
				self.log.info("Response chunk message size: %0.3fK. Sending", len(bmessage) / 1024.0)
				self.connector.put_response(bmessage, routing_key_override=routing_key_override)

	def process_messages(self, loops):

		msg_count = 0
		for message in self.connector.get_iterator():
			if not RUN_STATE or self.die:
				return

			if message:
				msg_count += 1
				self.log.info("Processing message. (%s of %s before connection reset)", msg_count, loops)

				try:
					early_acked, response, postDelay, routing_key_override = self._dispatch_binary_message(message)

					self.put_message_chunked(response, routing_key_override=routing_key_override)
					# connector_instance.put_response(response)

					if not early_acked:
						# Ack /after/ we've done the task.
						message.ack()

					self.successDelay(postDelay)

				except CannotHandleNow:
					self.log.warning("Message cannot be processed at this time. Returning to processing queue")
					# Push into dead-letter queue.
					message.reject(requeue=False)

				except Exception:
					self.log.warning("Failure when processing message!")
					# Push into dead-letter queue.
					message.reject(requeue=False)

			if msg_count > loops:
				return

	def processEvents(self):
		'''
		Connect to the server, wait for a task, and then disconnect untill another job is
		received.

		The AMQP connection is not maintained due to issues with long-lived connections.
		'''

		sslopts = findCert()
		self.connector = None

		try:
			while RUN_STATE and not self.die:
				try:
					self.log.info("Initializing AMQP Connection!")
					self.connector = amqp_connector.Connector(
									userid=self.settings["RABBIT_LOGIN"],
									password=self.settings["RABBIT_PASWD"],
									host=self.settings["RABBIT_SRVER"],
									virtual_host=self.settings["RPC_RABBIT_VHOST"],
									ssl=sslopts,
									prefetch=2,
									synchronous=True,
									task_exchange_type="direct",
									durable=True, )

					self.log.info("AMQP Connection initialized. Entering runloop!")

					self.process_messages(1000)
					self.connector.close()
					self.connector = None

				except IOError:
					self.log.error("Error while connecting to server.")
					self.log.error("Is the AMQP server not available?")
					for line in traceback.format_exc().split("\n"):
						self.log.error(line)
					self.log.error("Trying again in 30 seconds.")
					time.sleep(30)
					self.connector = None
					continue

				self.log.info("Connection Established. Awaiting RPC requests")

		except KeyboardInterrupt:
			self.log.info("Keyboard Interrupt exit!")
			self.die = True

		self.log.info("Halting message consumer.")
		try:
			self.connector.close()
		except Exception:
			self.log.error("Closing the connector produced an error!")
			for line in traceback.format_exc().split("\n"):
				self.log.error(line)

		self.log.info("Closed. Exiting")

		if not RUN_STATE or self.die:
			raise KeyboardInterrupt
