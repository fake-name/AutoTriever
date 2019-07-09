
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
			'heartbeat'                : kwargs.get('heartbeat',                  60),
			'sslopts'                  : kwargs.get('ssl',                      None),
			'poll_rate'                : kwargs.get('poll_rate',                0.25),
			'prefetch'                 : kwargs.get('prefetch',                    1),
			'session_fetch_limit'      : kwargs.get('session_fetch_limit',      None),
			'durable'                  : kwargs.get('durable',                 False),
			'socket_timeout'           : kwargs.get('socket_timeout',             30),
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

			# If we're set to durable, bind a Dead letter exchange to the main task queue,
			# and attach that dlq to a queue with a timeout that then dead-letters back
			# into the main queue.

			baseq_args = {}
			if self.config['durable']:
				dlex_name = self.config['task_exchange'] + ".dlq.e"
				dlq_name = self.config['task_queue_name'] + ".dlq.q"
				baseq_args["x-dead-letter-exchange"] = dlex_name

				dlq_args = {
					"x-dead-letter-exchange" : self.config['task_exchange'],
					"x-message-ttl"          : 30 * 1000
				}
				self.channel.exchange_declare(dlex_name, 'direct', auto_delete=False, durable=self.config['durable'])
				self.channel.queue_declare(dlq_name, auto_delete=False, durable=self.config['durable'], arguments=dlq_args)
				self.channel.queue_bind(dlq_name, exchange=dlex_name, routing_key=self.config['task_queue_name'].split(".")[0])

			# Clients need to declare their task queues, so the master can publish into them.
			self.channel.queue_declare(self.config['task_queue_name'], auto_delete=False, durable=self.config['durable'], arguments=baseq_args)
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

	def put_response(self, out_msg, routing_key_override=None):
		if self.config['master']:
			out_queue = self.config['task_exchange']
			out_key   = self.config['task_queue_name'].split(".")[0]
		else:
			out_queue = self.config['response_exchange']
			out_key   = self.config['response_queue_name'].split(".")[0]

		if routing_key_override:
			self.log.info("Response routing key overridden with value '%s'", routing_key_override)
			out_key = routing_key_override

		msg_prop = {}
		if self.config['durable']:
			# Is this supposed to be a hyphen or a underscore?
			msg_prop["delivery_mode"] = 2

		self.channel.basic_publish(body=out_msg, exchange=out_queue, routing_key=out_key, properties=msg_prop)

