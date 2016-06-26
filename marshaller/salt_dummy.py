

import sys
import pprint
import random
import logging
import json
import copy
import uuid

import settings
import logSetup



class VmInitError(RuntimeError):
	pass

class VpsHerder(object):

	def __init__(self):
		self.log = logging.getLogger("Main.TestVpsHerder")

	def make_client(self, clientname):

		self.log.info("Creating instance...")
		self.log.info("Instance created!")
		# instance = cc.create(names=['test-1'], provider=provider, **kwargs)
		# print(ret)




	def configure_client(self, clientname, client_idx):
		assert "_" not in clientname, "VM names cannot contain _ on digital ocean, I think?"
		self.log.info("Configuring client")

		self.log.info("Node configured! Starting scraper client!")


	def destroy_client(self, clientname):
		pass

	def list_nodes(self):
		'''
		Example response:
		{
		    'do': {
		        'digital_ocean': {
		            u 'test-1': {
		                'private_ips': [],
		                'image': u '14.04.4 x64',
		                'state': 'active',
		                'name': u 'test-1',
		                'public_ips': [u 'xxx.xxx.xxx.xxx'],
		                'id': 18105705,
		                'size': u '512mb'
		            }
		        }
		    }
		}
		'''
		nodes = ["test-node"]
		return nodes

if __name__ == '__main__':
	logSetup.initLogging()
	herder = VpsHerder()
	if "destroy" in sys.argv:
		herder.destroy_client("test-1")
	elif "list" in sys.argv:
		herder.list_nodes()
	elif "configure" in sys.argv:
		herder.configure_client("test-1", 0)
	else:
		herder.make_client("test-1")
		herder.configure_client("test-1", 0)
