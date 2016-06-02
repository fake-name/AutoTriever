#!/usr/bin/env python3
import traceback
import json
import AmqpConnector
import logging
import os.path
import ssl


class RabbitQueueHandler(object):
	die = False

	def __init__(self, settings, is_master=False):

		logPath = 'Main.NuScrape.AMQP'

		self.log = logging.getLogger(logPath)
		self.log.info("RPC Management class instantiated. Master: %s.", is_master)


		# Require clientID in settings
		assert "NU_RABBIT_LOGIN"       in settings
		assert "NU_RABBIT_PASWD"       in settings
		assert "NU_RABBIT_SRVER"       in settings
		assert "NU_RABBIT_VHOST"       in settings

		sslopts = self.getSslOpts()

		self.connector = AmqpConnector.Connector(userid            = settings["NU_RABBIT_LOGIN"],
												password           = settings["NU_RABBIT_PASWD"],
												host               = settings["NU_RABBIT_SRVER"],
												virtual_host       = settings["NU_RABBIT_VHOST"],
												ssl                = sslopts,
												master             = is_master,
												synchronous        = False,
												flush_queues       = False,
												prefetch           = 25,
												durable            = True,
												task_exchange_type = "fanout",
												task_queue         = 'nuresponse.master.q',
												response_queue     = 'nureleases.master.q',
												)


		self.log.info("Connected AMQP Interface: %s", self.connector)
		self.log.info("Connection parameters: %s, %s, %s, %s", settings["NU_RABBIT_LOGIN"], settings["NU_RABBIT_PASWD"], settings["NU_RABBIT_SRVER"], settings["NU_RABBIT_VHOST"])

	def getSslOpts(self):
		'''
		Verify the SSL cert exists in the proper place.
		'''
		certpaths = ['./rabbit_pub_cert/', '../rabbit_pub_cert/', './deps/']
		for certpath in certpaths:

			caCert = os.path.abspath(os.path.join(certpath, './cacert.pem'))
			cert = os.path.abspath(os.path.join(certpath, './cert.pem'))
			keyf = os.path.abspath(os.path.join(certpath, './key.pem'))

			try:
				assert os.path.exists(caCert), "No certificates found on path '%s'" % caCert
				assert os.path.exists(cert), "No certificates found on path '%s'" % cert
				assert os.path.exists(keyf), "No certificates found on path '%s'" % keyf
				print("Found certificates on path: ", certpath)
				break
			except AssertionError:
				traceback.print_exc()
				print("No certificates on path: ", certpath)


		ret = {"cert_reqs"  : ssl.CERT_REQUIRED,
				"ca_certs"  : caCert,
				"keyfile"   : keyf,
				"certfile"  : cert,
			}
		print("Certificate config: ", ret)

		return ret

	def put_item(self, data):
		# self.log.info("Putting data: %s", data)
		self.connector.putMessage(data, synchronous=1000)
		# self.log.info("Outgoing data size: %s bytes.", len(data))


	def get_item(self):
		ret = self.connector.getMessage()
		self.log.info("Received data size: %s bytes.", len(ret))
		return ret


	def __del__(self):
		self.close()

	def close(self):
		if self.connector:
			self.connector.stop()
			self.connector = None

	def putRow(self, row):

		message = {
			"nu_release" : {
				"seriesname"       : row.seriesname,
				"releaseinfo"      : row.releaseinfo,
				"groupinfo"        : row.groupinfo,
				"referrer"         : row.referrer,
				"outbound_wrapper" : row.outbound_wrapper,
				"actual_target"    : row.actual_target,
				"addtime"          : row.addtime.isoformat(),
			}
		}
		msg = json.dumps(message)
		self.put_item(msg)

