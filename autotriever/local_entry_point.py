
import gevent
import gevent.monkey
from gevent.server import StreamServer

import logging
import threading
import queue
import threading
import pickle
import sys
import time
import json
import queue
import os
import signal
import traceback

import mprpc

gevent.monkey.patch_all()

from .deps import logSetup
from . import dispatcher



INTERRUPTS = 0
TO_EXIT    = []
SOCK_PATH  = '/tmp/rwp-fetchagent-sock'

def build_mprpc_handler(server):
	global TO_EXIT
	TO_EXIT.append(server)

	def handler(signum=-1, frame=None):
		global INTERRUPTS
		INTERRUPTS += 1
		print('Signal handler called with signal %s for the %s time' % (signum, INTERRUPTS))
		if INTERRUPTS > 2:
			print("Raising due to repeat interrupts")
			raise KeyboardInterrupt
		for server in TO_EXIT:
			server.close()
	return handler

def base_abort():
	print("Low level keyboard interrupt")
	for server in TO_EXIT:
		server.close()



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



class FetchInterfaceClass(mprpc.RPCServer):
	def __init__(self, settings, lock_dict):

		mp_conf = {"use_bin_type":True}
		super().__init__(pack_params=mp_conf)

		self.log = logging.getLogger("Main.RPC-Interface")
		self.dispatcher = dispatcher.RpcCallDispatcher(
				settings  = settings,
				lock_dict = lock_dict,
			)

		self.log.info("Connection")

	def dispatch_request(self, params):
		try:
			return self.dispatcher.process(params, context_responder=None, lock_interface=None)

		except Exception as exc:

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

			return response

	def checkOk(self):
		return (True, b'wattt\0')




def run_rpc(interface_dict, settings):
	print("MpRPC server Started.")
	server_instance = FetchInterfaceClass(settings=settings, lock_dict=interface_dict)
	mprpc_server = StreamServer(('0.0.0.0', 4315), server_instance)
	handler = build_mprpc_handler(mprpc_server)

	gevent.signal.signal(signal.SIGINT, handler)
	mprpc_server.serve_forever()


def initialize_manager():

	interface_dict = {}
	# interface_dict.qlock = pickle.dumps(mgr.Lock())
	interface_dict['qlock'] = threading.Lock()

	interface_dict['outq'] = {}
	interface_dict['inq'] = {}

	interface_dict['feed_outq'] = {}
	interface_dict['feed_inq'] = {}

	return interface_dict

def run():

	settings = loadSettings()
	logSetup.initLogging()

	# Make sure the socket does not already exist
	try:
		os.unlink(SOCK_PATH)
	except OSError:
		if os.path.exists(SOCK_PATH):
			raise


	try:
		interface_dict = initialize_manager()
		run_rpc(interface_dict, settings)

	except AssertionError:
		print("Main worker encountered assertion failure!")
		traceback.print_exc()
		base_abort()
	except KeyboardInterrupt:
		print("Main worker abort")
		base_abort()

	except Exception:
		print("Wat?")
		traceback.print_exc()
		with open("Manager error %s.txt" % time.time(), "w") as fp:
			fp.write("Manager crashed?\n")
			fp.write(traceback.format_exc())

		raise


def go():
	print("Preloading cache directories")

	# print("Testing reload")
	# server.tree.tree.reloadTree()
	# print("Starting RPC server")
	try:
		run()

	except:
		# abort /hard/ if we exceptioned out of the main run.
		# This should (hopeully) cause the OS to terminate any
		# remaining threads.
		# As it is, I've been having issues with the main thread failing
		# with 'OSError: [Errno 24] Too many open files', killing the main thread
		# and leaving some of the amqp interface threads dangling.
		# Somehow, it's not being caught in the `except Exception:` handler
		# in run(). NFI how.
		import ctypes
		ctypes.string_at(0)





if __name__ == '__main__':
	go()
