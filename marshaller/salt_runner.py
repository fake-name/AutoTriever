

import sys
import pprint
import random
import logging
import json
import copy
import uuid

import settings

import salt.cloud
import salt.client
import salt.config

import logSetup


SETTINGS_BASE = {
	"note1" : "Connection settings for the RabbitMQ server.",

	"RABBIT_LOGIN" : None,
	"RABBIT_PASWD" : None,
	"RABBIT_SRVER" : None,

	"clientid"     : None,

	"note2" : "ExHentai/E-Hentai login",
	"sadPanda" : {
		"login"         : None,
		"passWd"        : None
	},

	"NU_ENABLE"       : True,

	"RPC_RABBIT_VHOST" : "/rpcsys",
	"NU_RABBIT_VHOST"  : "/nu-feeds",

}


class VpsHerder(object):

	def __init__(self):
		self.log = logging.getLogger("Main.VpsHerder")
		self.local = salt.client.LocalClient()
		self.cc = salt.cloud.CloudClient('/etc/salt/cloud')

	def __make_conf_file(self, client_id, client_idx):
		assert client_idx < len(settings.mq_accts)

		conf = copy.copy(SETTINGS_BASE)
		conf['RABBIT_LOGIN'] = settings.mq_accts[client_idx]['login']
		conf['RABBIT_PASWD'] = settings.mq_accts[client_idx]['passwd']
		conf['RABBIT_SRVER'] = settings.RABBIT_SERVER

		conf['clientid'] = client_id
		conf['client_key'] = uuid.uuid4().urn

		conf['sadPanda']['login']  = settings.EX_LOGIN
		conf['sadPanda']['passWd'] = settings.EX_PASSW

		return json.dumps(conf)



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

			# Install settings
			['cmd.run', ["cat << EOF > /scraper/settings.json \n{content}\nEOF".format(content=self.__make_conf_file("test-1", 0)), ], {}],

			# Finally, run the thing
			['cmd.run', ["./configure.sh", ], {"cwd" : '/scraper'}],
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

		self.log.info("Node configured! Starting scraper client!")
		jobid = self.local.cmd_async(command='cmd.run', arg=["./run.sh", ], kwarg={"cwd" : '/scraper'})
		self.log.info("Job id: '%s'", jobid)


	def destroy_client(self, clientname):
		self.cc.destroy(clientname)
		# images = cc.list_images()
		# locs   = cc.list_locations()
		# sizes  = cc.list_sizes()
		# pprint.pprint(images)
		# pprint.pprint(locs)
		# pprint.pprint(sizes)

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
		self.log.info("Active nodes: %s", self.cc.query())

	def dump_minion_conf(self):
		conf = salt.config.client_config('/etc/salt/minion')
		self.log.info(conf)

if __name__ == '__main__':
	logSetup.initLogging()
	herder = VpsHerder()
	if "destroy" in sys.argv:
		herder.destroy_client("test-1")
	elif "list" in sys.argv:
		herder.list_nodes()
	else:
		herder.make_client("test-1")
		herder.configure_client("test-1")
