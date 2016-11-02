#!/usr/bin/env python3
import msgpack
import rabbitpy
import urllib.parse
import logging
import uuid
import os.path
import threading
import ssl
import time
import traceback
from state import RUN_STATE

# CHUNK_SIZE_BYTES = 250 * 1024
CHUNK_SIZE_BYTES = 100 * 1024

def chunk_input(inval, chunk_size):
	for i in range(0, len(inval), chunk_size):
		yield inval[i:i+chunk_size]

class Connector:
	def __init__(self, *args, **kwargs):


		config = {
			'host'                     : kwargs.get('host',                     None),
			'userid'                   : kwargs.get('userid',                   'guest'),
			'password'                 : kwargs.get('password',                 'guest'),
			'virtual_host'             : kwargs.get('virtual_host',             '/'),
			'task_queue_name'          : kwargs.get('task_queue',               'task.q'),
			'response_queue_name'      : kwargs.get('response_queue',           'response.q'),
			'task_exchange'            : kwargs.get('task_exchange',            'tasks.e'),
			'task_exchange_type'       : kwargs.get('task_exchange_type',       'direct'),
			'response_exchange'        : kwargs.get('response_exchange',        'resps.e'),
			'response_exchange_type'   : kwargs.get('response_exchange_type',   'direct'),
			'master'                   : kwargs.get('master',                   False),
			'synchronous'              : kwargs.get('synchronous',              True),
			'flush_queues'             : kwargs.get('flush_queues',             False),
			'heartbeat'                : kwargs.get('heartbeat',                 30),
			'sslopts'                  : kwargs.get('ssl',                      None),
			'poll_rate'                : kwargs.get('poll_rate',                0.25),
			'prefetch'                 : kwargs.get('prefetch',                    1),
			'session_fetch_limit'      : kwargs.get('session_fetch_limit',      None),
			'durable'                  : kwargs.get('durable',                 False),
			'socket_timeout'           : kwargs.get('socket_timeout',             10),

		}



		assert 'host'                     in config
		assert 'userid'                   in config
		assert 'password'                 in config
		assert 'virtual_host'             in config
		assert 'task_queue_name'          in config
		assert 'response_queue_name'      in config
		assert 'task_exchange'            in config
		assert 'task_exchange_type'       in config
		assert 'response_exchange'        in config
		assert 'response_exchange_type'   in config
		assert 'master'                   in config
		assert 'synchronous'              in config
		assert 'flush_queues'             in config
		assert 'heartbeat'                in config
		assert 'sslopts'                  in config
		assert 'poll_rate'                in config
		assert 'prefetch'                 in config
		assert 'session_fetch_limit'      in config
		assert 'durable'                  in config
		assert 'socket_timeout'           in config


		self.log = logging.getLogger("Main.Connector.Internal(%s)" % config['virtual_host'])
		self.config             = config


		self.last_hearbeat_sent     = time.time()
		self.last_hearbeat_received = time.time()

		self.sent_messages = 0
		self.recv_messages = 0

		self.connection     = None
		self.channel        = None

		self.keepalive_exchange_name = "keepalive_exchange"+str(id("wat"))

		self.delivered = 0
		self.active_connections = 0

		self._connect()




	def __del__(self):
		try:
			self.close()
		except Exception:
			pass

		# Force everything closed, because we seem to have two instances somehow
		self.connection     = None
		self.channel        = None
		self.config         = None

		# Finally, deincrement the active count
		self.active_connections = 0


	def _connect(self):

		assert self.active_connections == 0
		self.active_connections = 1


		qs = urllib.parse.urlencode({
			'cacertfile'           :self.config['sslopts']['ca_certs'],
			'certfile'             :self.config['sslopts']['certfile'],
			'keyfile'              :self.config['sslopts']['keyfile'],

			'verify'               : 'ignore',
			'heartbeat'            : self.config['heartbeat'],

			'connection_timeout'   : self.config['socket_timeout'],

			})

		uri = '{scheme}://{username}:{password}@{host}:{port}/{virtual_host}?{query_str}'.format(
			scheme       = 'amqps',
			username     = self.config['userid'],
			password     = self.config['password'],
			host         = self.config['host'].split(":")[0],
			port         = self.config['host'].split(":")[1],
			virtual_host = self.config['virtual_host'],
			query_str    = qs,
			)
		self.log.info("Initializing AMQP connection.")
		self.connection = rabbitpy.Connection(uri)
		# self.connection.connect()

		self.log.info("Connected. Creating channel.")

		# Channel and exchange setup
		self.channel = rabbitpy.AMQP(self.connection.channel(blocking_read = True))
		self.log.info("Setting QoS.")


		self.log.info("Connection established. Setting up consumer.")

		if self.config['flush_queues']:
			self.log.info("Flushing items in queue.")
			self.channel.queue_purge(self.config['task_queue_name'])
			self.channel.queue_purge(self.config['response_queue_name'])

		self.log.info("Configuring queues.")
		self._setupQueues()

		if self.config['master']:
			self.in_queue = self.config['response_queue_name']
		else:
			self.in_queue = self.config['task_queue_name']

		qchan = self.connection.channel()
		qchan.prefetch_count(self.config['prefetch'])
		self.in_q = rabbitpy.Queue(qchan, self.in_queue)


	def _setupQueues(self):

		self.channel.exchange_declare(self.config['task_exchange'],     exchange_type=self.config['task_exchange_type'],     auto_delete=False, durable=self.config['durable'])
		self.channel.exchange_declare(self.config['response_exchange'], exchange_type=self.config['response_exchange_type'], auto_delete=False, durable=self.config['durable'])

		# set up consumer and response queues
		if self.config['master']:
			# Master has to declare the response queue so it can listen for responses
			self.channel.queue_declare(self.config['response_queue_name'], auto_delete=False, durable=self.config['durable'])
			self.channel.queue_bind(   self.config['response_queue_name'], exchange=self.config['response_exchange'], routing_key=self.config['response_queue_name'].split(".")[0])
			self.log.info("Binding queue %s to exchange %s.", self.config['response_queue_name'], self.config['response_exchange'])

		if not self.config['master']:
			# Clients need to declare their task queues, so the master can publish into them.
			self.channel.queue_declare(self.config['task_queue_name'], auto_delete=False, durable=self.config['durable'])
			self.channel.queue_bind(   self.config['task_queue_name'], exchange=self.config['task_exchange'], routing_key=self.config['task_queue_name'].split(".")[0])
			self.log.info("Binding queue %s to exchange %s.", self.config['task_queue_name'], self.config['task_exchange'])

		# "NAK" queue, used for keeping the event loop ticking when we
		# purposefully do not want to receive messages
		# THIS IS A SHITTY WORKAROUND for keepalive issues.
		self.channel.exchange_declare(self.keepalive_exchange_name, exchange_type="direct", auto_delete=True, durable=False, arguments={"x-expires" : 5*60*1000})
		self.channel.queue_declare('nak.q', auto_delete=False, durable=False)
		self.channel.queue_bind('nak.q',    exchange=self.keepalive_exchange_name, routing_key="nak")



	def close(self):
		# Stop the flow of new items
		self.channel.basic_qos(
				prefetch_size  = 0,
				prefetch_count = 0,
				global_flag    = False
			)

		# Close the connection once it's empty.
		try:
			# self.in_q.stop_consuming()
			self.connection.close()
		except rabbitpy.exceptions.RabbitpyException as e:
			# We don't really care about exceptions on teardown
			self.log.error("Error on interface teardown!")
			self.log.error("	%s", e)
			# for line in traceback.format_exc().split('\n'):
			# 	self.log.error(line)

		self.log.info("AMQP Thread exited")


	def get_iterator(self):
		# self.log.info("Consuming item from queue")
		return self.in_q.consume()
		# # ret = self.channel.basic_get()
		# if ret:
		# 	self.log.info("Item fetched from queue.")
		# return ret

	def put_response(self, out_msg):
		if self.config['master']:
			out_queue = self.config['task_exchange']
			out_key   = self.config['task_queue_name'].split(".")[0]
		else:
			out_queue = self.config['response_exchange']
			out_key   = self.config['response_queue_name'].split(".")[0]

		msg_prop = {}
		if self.config['durable']:
			msg_prop["delivery_mode"] = 2
		self.channel.basic_publish(body=out_msg, exchange=out_queue, routing_key=out_key, properties=msg_prop)

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

			if 'jobmeta' in body:
				ret['jobmeta'] = body['jobmeta']

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

			if 'jobmeta' in body:
				ret['jobmeta'] = body['jobmeta']

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
		ret['user_uuid'] = self.settings['client_key']

		self.log.info("Returning")


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



	def process_messages(self, connector, loops):

		msg_count = 0
		for message in connector.get_iterator():
			if not RUN_STATE or self.die:
				return

			if message:
				msg_count += 1
				self.log.info("Processing message. (%s of %s before connection reset)", msg_count, loops)

				response, postDelay = self._process(message.body)

				self.put_message_chunked(response, connector)
				# connector.put_response(response)

				# Ack /after/ we've done the task.
				message.ack()


				self.successDelay(postDelay)

			if msg_count > loops:
				return
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
					self.log.info("Initializing AMQP Connection!")
					connector = Connector(userid              = self.settings["RABBIT_LOGIN"],
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

					self.process_messages(connector, 20)
					connector.close()
					connector = None

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
			connector.close()
		except Exception:
			self.log.error("Closing the connector produced an error!")
			for line in traceback.format_exc().split("\n"):
				self.log.error(line)


		self.log.info("Closed. Exiting")

		if not RUN_STATE or self.die:
			raise KeyboardInterrupt
