

import sys
import pprint
import random
import logging
import json
import copy
import uuid
import traceback

import settings

import salt.cloud
import salt.exceptions
import salt.client
import salt.config
import salt.exceptions

import marshaller_exceptions
import logSetup
import os.path

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

	"threads"  : 5,

}

class VmInitError(RuntimeError):
	pass

dirmake_oneliner = 'python -c \'import os.path, sys, os; os.makedirs("/scraper") if not os.path.exists("/scraper") else None; print("Dir exists and is dir: ", os.path.isdir("/scraper"));sys.exit(1 if os.path.isdir("/scraper") else 0);\''

class VpsHerder(object):

	def __init__(self):
		self.log = logging.getLogger("Main.VpsHerder")
		try:
			self.local = salt.client.LocalClient()
		except ImportError:
			print("No local salt.client.LocalClient. Running without, may cause errors!")
		except salt.exceptions.SaltClientError:
			print("Cannot load salt master configuration!")
		except IOError:
			print("Cannot load salt master configuration!")

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


	def get_512_meta(self):
		self.log.info("Vultr test")
		sizes = self.cc.list_sizes(provider='vultr')['vultr']['vultr']
		for name, size_meta in sizes.items():
			if float(size_meta['price_per_month']) <= 5.0:
				return size_meta['VPSPLANID'], size_meta['available_locations']

		return None, None

	def generate_vultr_conf(self):

		provider = "vultr"

		planid, places = self.get_512_meta()

		if not planid:
			raise marshaller_exceptions.VmCreateFailed("No vultr plan available?")

		scriptname = "bootstrap-salt-delay.sh"
		scriptdir  = os.path.dirname(os.path.realpath(__file__))
		fqscript = os.path.join(scriptdir, scriptname)

		kwargs = {
			'image'              : 'Ubuntu 16.04 x64',
			'private_networking' : False,
			'size'               : planid,
			'location'           : random.choice(places),
			'script'             : fqscript,
			'script_args'        : "-D",


		}
		return provider, kwargs

	def generate_conf(self):
		# TODO: Vultr goes here too
		return random.choice([self.generate_do_conf, self.generate_vultr_conf])()
		# return random.choice([self.generate_do_conf])()

	def make_client(self, clientname):

		provider, kwargs = self.generate_conf()
		self.log.info("Creating instance...")
		self.log.info("	Client name: '%s'", clientname)
		self.log.info("	using provider: '%s'", provider)
		self.log.info("	kwargs: '%s'", kwargs)
		try:
			ret = self.cc.create(names=[clientname], provider=provider, **kwargs)
			self.log.info("Instance created!")
		except Exception as e:
			traceback.print_exc()
			raise marshaller_exceptions.VmCreateFailed("Failed when creating VM? Exception: %s" % e)
		# instance = cc.create(names=['test-1'], provider=provider, **kwargs)
		# print(ret)


	def configure_client(self, clientname, client_idx):
		assert "_" not in clientname, "VM names cannot contain _ on digital ocean, I think?"
		self.log.info("Configuring client")

		commands = [
			['cmd.run', [dirmake_oneliner, ],      {}],
			['cmd.run', ["apt-get install -y build-essential git screen", ],      {}],
			['cmd.run', ["git clone https://github.com/fake-name/AutoTriever.git /scraper"], {}],
			['cmd.run', ["ls /scraper", ], {}],
			['cmd.run', ["whoami", ], {}],

			# Make swap so
			['cmd.run', ["dd if=/dev/zero of=/swapfile bs=1M count=1024", ], {}],
			['cmd.run', ["mkswap /swapfile", ], {}],
			['cmd.run', ["swapon /swapfile", ], {}],
			['cmd.run', ["dpkg-reconfigure locales", ], {}],
			['cmd.run', ['echo LANG=\"en_US.UTF-8\" >> /etc/default/locale', ], {}],
			['cmd.run', ['echo LC_ALL=\"en_US.UTF-8\" >> /etc/default/locale', ], {}],
			['cmd.run', ["dpkg-reconfigure locales", ], {}],
			['cmd.run', ["locale", ], {}],
			['cmd.run', ["bash -c locale", ], {}],

			# Install settings
			['cmd.run', ["cat << EOF > /scraper/settings.json \n{content}\nEOF".format(content=self.__make_conf_file(clientname, client_idx)), ], {}],

			# Finally, run the thing
			['cmd.run', ["./configure.sh", ], {"cwd" : '/scraper'}],
		]

		failures = 0

		for command, args, kwargs in commands:
			while True:
				self.log.info("Executing command '%s', args: '%s', kwargs: '%s'", command, args, kwargs)
				resp = self.local.cmd(clientname,
					fun=command,
					arg=args,
					kwarg=kwargs
					)
				self.log.info("Command executed. Clientname in response: %s", clientname in resp)
				if clientname in resp:
					failures = 0
					break
				else:
					failures += 1
					tries = 3
					self.log.error("Command failed (attempt %s of %s)!", failures, tries)
					self.log.error("Response:")
					self.log.error("%s", resp)
					if failures > tries:
						raise marshaller_exceptions.VmCreateFailed("Failed to create VM!")

			if resp[clientname]:
				for line in resp[clientname].split("\n"):
					self.log.info("	%s", line)
			else:
				self.log.info("Received empty response")


		if not resp[clientname].strip().endswith('Setup OK! System is configured for launch'):
			raise VmInitError("Setup command did not return success!")

		self.log.info("Node configured! Starting scraper client!")
		jobid = self.local.cmd_async(tgt=clientname, fun='cmd.run', arg=["screen -d -m ./run.sh", ], kwarg={"cwd" : '/scraper'})
		self.log.info("Job id: '%s'", jobid)


	def destroy_client(self, clientname):
		self.log.info("Destroying client named: '%s'", clientname)
		loops = 1
		while clientname in self.list_nodes():
			try:
				self.log.info("Destroying.... %s", loops)
				ret = self.cc.destroy(clientname)
				print(ret)
				return
			except salt.exceptions.SaltCloudSystemExit:
				self.log.error("Failed to destroy: %s", clientname)
				pass
			loops += 1

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
		nodes = []
		nodelist = self.cc.query()
		if 'do' in nodelist:
			if 'digital_ocean' in nodelist['do']:
				for key, nodedict in nodelist['do']['digital_ocean'].items():
					nodes.append(nodedict['name'].encode("ascii"))
		if 'vultr' in nodelist:
			if 'vultr' in nodelist['vultr']:
				for key, nodedict in nodelist['vultr']['vultr'].items():
					if key:
						nodes.append(key.encode("ascii"))
		self.log.info("Active nodes: %s", nodes)
		return nodes

	def dump_minion_conf(self):
		conf = salt.config.client_config('/etc/salt/minion')
		self.log.info(conf)

	def list_vultr_options(self):
		self.log.info("Vultr test")
		images = self.cc.list_images(provider='vultr')
		sizes = self.cc.list_sizes(provider='vultr')['vultr']['vultr']
		pprint.pprint(images)
		pprint.pprint(sizes)
		for name, size in sizes.items():
			print(int(size['ram']) == 768)

	def list_do_options(self):
		self.log.info("DO test")
		images = self.cc.list_images(provider='do')
		sizes = self.cc.list_sizes(provider='do')
		pprint.pprint(images)
		pprint.pprint(sizes)
		pass


# So.... vultur support is currently fucked.
# Waiting on https://github.com/saltstack/salt/issues/37040

def vtest():
	clientname = "test-1"
	provider, kwargs = herder.generate_vultr_conf()
	herder.log.info("Creating instance...")
	herder.log.info("	Client name: '%s'", clientname)
	herder.log.info("	using provider: '%s'", provider)
	herder.log.info("	kwargs: '%s'", kwargs)
	ret = herder.cc.create(names=[clientname], provider=provider, **kwargs)
	print("Create response:", ret)

	# herder.configure_client(clientname, 0)
	herder.log.info("Instance created!")


def dtest():
	clientname = "test-1"
	provider, kwargs = herder.generate_do_conf()
	herder.log.info("Creating instance...")
	herder.log.info("	Client name: '%s'", clientname)
	herder.log.info("	using provider: '%s'", provider)
	herder.log.info("	kwargs: '%s'", kwargs)
	ret = herder.cc.create(names=[clientname], provider=provider, **kwargs)
	print("Create response:", ret)

	# herder.configure_client(clientname, 0)
	herder.log.info("Instance created!")



if __name__ == '__main__':
	logSetup.initLogging()
	herder = VpsHerder()

	# herder.list_vultr_options()
	# herder.list_do_options()

	if "vtest" in sys.argv:
		vtest()

	elif "destroy-all" in sys.argv:
		while herder.list_nodes():
			for node in herder.list_nodes():
				herder.destroy_client(node)
	elif "destroy" in sys.argv:
		herder.destroy_client("test-1")
	elif "brute-vtest" in sys.argv:
		while 1:
			vtest()
			herder.destroy_client("test-1")
	elif "brute-dtest" in sys.argv:
		while 1:
			dtest()
			herder.destroy_client("test-1")
	elif "list" in sys.argv:
		herder.list_nodes()
	elif "configure" in sys.argv:
		herder.configure_client("test-1", 0)
	else:
		herder.make_client("test-1")
		herder.configure_client("test-1", 0)

