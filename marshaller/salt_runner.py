

import sys
import pprint
import random
import logging

import salt.cloud
import salt.client
import salt.config

import logSetup

class VpsHerder(object):

	def __init__(self):
		self.log = logging.getLogger("Main.VpsHerder")
		self.local = salt.client.LocalClient()
		self.cc = salt.cloud.CloudClient('/etc/salt/cloud')


	def generate_do_conf(self):

		provider = "do"
		kwargs = {
			'image': 'ubuntu-14-04-x64',
			'size': '512mb',
			'vm_size': '512mb',
			'private_networking' : False,
			'location' : random.choice(['ams2', 'ams3', 'blr1', 'fra1', 'lon1', 'nyc1', 'nyc2', 'nyc3', 'sfo1', 'sgp1', 'tor1']),


		}
		return provider, kwargs

	def generate_conf(self):
		# TODO: Vultr goes here too
		return random.choice([self.generate_do_conf])()

	def make_client(self, clientname):

		provider, kwargs = self.generate_conf()
		self.log.info("Creating instance...")
		self.log.info("	Client name: '%s'", clientname)
		self.log.info("	using provider: '%s'", provider)
		self.log.info("	kwargs: '%s'", kwargs)
		ret = self.cc.create(names=[clientname], provider=provider, **kwargs)
		self.log.info("Instance created!")
		# instance = cc.create(names=['test-1'], provider=provider, **kwargs)
		# print(ret)





	def configure_client(self, clientname):
		assert "_" not in clientname, "VM names cannot contain _ on digital ocean, I think?"
		self.log.info("Configuring client")

		commands = [
			['cmd.run', ["mkdir -p /scraper", ],      {}],
			['cmd.run', ["apt-get install -y build-essential git", ],      {}],
			['cmd.run', ["git clone https://github.com/fake-name/AutoTriever.git /scraper"], {}],
			['cmd.run', ["ls /scraper", ], {}],
			['cmd.run', ["whoami", ], {}],

			# Make swap so
			['cmd.run', ["dd if=/dev/zero of=/swapfile bs=1M count=1024", ], {}],
			['cmd.run', ["mkswap /swapfile", ], {}],
			['cmd.run', ["swapon /swapfile", ], {}],
			['cmd.run', ["./run.sh", ], {"cwd" : '/scraper'}],
		]

		for command, args, kwargs in commands:
			self.log.info("Executing command '%s', args: '%s', kwargs: '%s'", command, args, kwargs)
			resp = self.local.cmd(clientname,
				fun=command,
				arg=args,
				kwarg=kwargs
				)
			assert clientname in resp
			if resp[clientname]:
				for line in resp[clientname].split("\n"):
					self.log.info("	%s", line)
			else:
				self.log.info("Received empty response")



	def destroy_client(self, clientname):
		cc = salt.cloud.CloudClient('/etc/salt/cloud')

		cc.destroy(clientname)
		# images = cc.list_images()
		# locs   = cc.list_locations()
		# sizes  = cc.list_sizes()
		# pprint.pprint(images)
		# pprint.pprint(locs)
		# pprint.pprint(sizes)

	def dump_minion_conf(self):
		conf = salt.config.client_config('/etc/salt/minion')
		self.log.info(conf)

if __name__ == '__main__':
	logSetup.initLogging()
	herder = VpsHerder()
	if "destroy" in sys.argv:
		herder.destroy_client("test-1")
	else:
		# herder.make_client("test-1")
		herder.configure_client("test-1")
