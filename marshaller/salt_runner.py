

import sys
import pprint
import random
import logging
import json
import copy
import traceback
import uuid
import ast
import string

import settings

import salt.cloud
import salt.exceptions
import salt.client
import salt.config
import salt.exceptions

import marshaller_exceptions
import logSetup
import os.path
import statsd


def gen_random_string(length):
	if not hasattr(gen_random_string, "rng"):
		gen_random_string.rng = random.SystemRandom() # Create a static variable
	return ''.join([ gen_random_string.rng.choice(string.ascii_letters + string.digits) for _ in xrange(length) ])


MAX_MONTHLY_PRICE_DOLLARS = 5.0

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

dirmake_ssh_oneliner = 'python -c \'import os.path, sys, os; os.makedirs(".ssh/") if not os.path.exists(".ssh/") else None; print("Dir exists and is dir: ", os.path.isdir(".ssh/"));sys.exit(1 if os.path.isdir(".ssh/") else 0);\''
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


		self.mon_con = statsd.StatsClient(
				host = settings.GRAPHITE_DB_IP,
				port = 8125,
				prefix = 'ReadableWebProxy.VpsHerder',
				)


	################################################################################################
	# Digital Ocean
	################################################################################################

	def get_5_dollar_do_meta(self):
		self.log.info("Generating DO Configuration")

		sizes = self.cc.list_sizes(provider='digital_ocean')['digital_ocean']['digital_ocean']
		items = []

		for name, size_meta in sizes.items():
			if float(size_meta['price_monthly']) <= MAX_MONTHLY_PRICE_DOLLARS:

				# Why the fuck is this a string?
				size_meta['regions'] = ast.literal_eval(size_meta['regions'])

				for loc in size_meta['regions']:
					items.append((name, loc))

		self.log.info("Found %s potential VPS location/configurations", len(items))
		return random.choice(items)

	def generate_do_conf(self):

		try:
			planid, place = self.get_5_dollar_do_meta()
		except TypeError as e:
			raise  marshaller_exceptions.VmCreateFailed("Failed when creating VM configuration? Exception: %s" % e)

		provider = "digital_ocean"
		kwargs = {
			'image': 'ubuntu-14-04-x64',
			'size': planid,
			# 'vm_size': planid,
			'private_networking' : False,
			'location' : place,
		}

		return provider, kwargs

	################################################################################################
	# Vultr
	################################################################################################

	def get_5_dollar_vultr_meta(self):
		self.log.info("Generating Vultr Configuration")
		sizes = self.cc.list_sizes(provider='vultr')['vultr']['vultr']
		items = []

		for name, size_meta in sizes.items():
			if float(size_meta['price_per_month']) <= MAX_MONTHLY_PRICE_DOLLARS:
				print("Item:", name, size_meta)
				for loc in size_meta['available_locations']:
					items.append((size_meta['VPSPLANID'], loc))
		self.log.info("Found %s potential VPS location/configurations", len(items))
		return random.choice(items)

	def generate_vultr_conf(self):

		provider = "vultr"

		try:
			planid, place = self.get_5_dollar_vultr_meta()
		except TypeError as e:
			raise  marshaller_exceptions.VmCreateFailed("Failed when creating VM configuration? Exception: %s" % e)

		if not planid:
			raise marshaller_exceptions.VmCreateFailed("No vultr plan available?")

		scriptname = "bootstrap-salt-delay.sh"
		scriptdir  = os.path.dirname(os.path.realpath(__file__))
		fqscript = os.path.join(scriptdir, scriptname)

		kwargs = {
			'image'              : 'Ubuntu 16.04 x64',
			'private_networking' : False,
			'size'               : planid,
			'location'           : place,

			'script'             : fqscript,
			'script_args'        : "-D",
		}

		return provider, kwargs

	################################################################################################
	# Linode
	################################################################################################

	def get_linode_5_bux_meta(self):
		sizes     = self.cc.list_sizes(provider='linode')['linode']['linode']
		locations = self.cc.list_locations(provider='linode')['linode']['linode']
		sizel = []
		locl = []
		for name, size_meta in sizes.items():
			if size_meta[u'PRICE'] <= 5:
				sizel.append(name)


		for name, loc_meta in locations.items():
			locl.append(name)

		return sizel, locl

	def generate_linode_conf(self):

		provider = "linode"

		plans, places = self.get_linode_5_bux_meta()

		scriptname = "bootstrap-salt-delay.sh"
		scriptdir  = os.path.dirname(os.path.realpath(__file__))
		fqscript = os.path.join(scriptdir, scriptname)

		kwargs = {
			# 'image'              : 'Ubuntu 16.04 x64',
			# 'private_networking' : False,
			# 'size'               : planid,
			# 'location'           : random.choice(places),

			'size'     : random.choice(plans),
			'image'    : u'Ubuntu 16.04 LTS',
			'location' : random.choice(places),

			'script'             : fqscript,
			'script_args'        : "-D",

			'password'           : gen_random_string(32),
		}

		self.log.info("Linode VM will use password: '%s'", kwargs['password'])

		return provider, kwargs

	################################################################################################
	# GCE
	################################################################################################

	def get_gce_5_bux_meta(self):
		self.cc.action(fun='update_pricing', provider='gce')
		# sizes     = self.cc.list_sizes(provider='gce')['gce']['gce']
		locations = self.cc.list_locations(provider='gce')['gce']['gce']

		images = self.cc.list_images(provider='gce')['gce']['gce']

		image = None
		for key in images:
			if key.startswith('ubuntu-1604-xenial-'):
				image = key

		# pprint.pprint(sizes)
		# pprint.pprint(locations)

		# for item in sizes:
		# 	print(item['name'], item['price'])

		# ATM, the only instance size I want is the f1-micro
		# I want a preemptible instance (it's REALLY cheap), but
		# I haven't figured out how to extract the preemptible
		# instance pricing, so just hard-code it.
		size = 'f1-micro'

		locl = []
		for name, dummy_loc_meta in locations.items():
			locl.append(name)

		return image, size, locl

	def generate_gce_conf(self):

		provider = "gce"

		image, size, places = self.get_gce_5_bux_meta()
		if not image:
			raise VmInitError("No Ubuntu 16.04 image found!")

		scriptname = "bootstrap-salt-delay.sh"
		scriptdir  = os.path.dirname(os.path.realpath(__file__))
		fqscript = os.path.join(scriptdir, scriptname)

		kwargs = {
			# 'image'              : 'Ubuntu 16.04 x64',
			# 'private_networking' : False,
			# 'size'               : planid,
			# 'location'           : random.choice(places),

			'size'     : size,
			'image'    : image,
			'location' : random.choice(places),

			'script'             : fqscript,
			'script_args'        : "-D",

			# I think the gce driver maps 'preemptible' to 'ex_preemptible'
			# Pass both anyways.
			'preemptible'        : True,
			'ex_preemptible'     : True,
		}

		return provider, kwargs

	################################################################################################
	# Scaleway
	################################################################################################

	def generate_scaleway_conf(self):

		provider = "scaleway"

		scriptname = "bootstrap-salt-delay.sh"
		scriptdir  = os.path.dirname(os.path.realpath(__file__))
		fqscript = os.path.join(scriptdir, scriptname)

		# I dunno if this is correct.
		opt_tups = [
			('C1',        'Paris'),
			('VC1S',      'Paris'),
			('ARM64-2GB', 'Paris'),
			('VC1S',      'Amsterdam'),
			('ARM64-2GB', 'Amsterdam'),
		]

		size, location = random.choice(opt_tups)

		kwargs = {
			# 'image'              : 'Ubuntu 16.04 x64',
			# 'private_networking' : False,
			# 'size'               : planid,
			# 'location'           : random.choice(places),

			'size'     : size,
			'image'    : u'Ubuntu Xenial (16.04 latest)',
			'location' : location,

			'script'             : fqscript,
			'script_args'        : "-D",

			# 'password'           : gen_random_string(32),
		}

		# self.log.info("Scaleway VM will use password: '%s'", kwargs['password'])


		return provider, kwargs

	################################################################################################
	# Choice selector
	################################################################################################

	def generate_conf(self):
		gen_calls = [
				self.generate_do_conf,
				self.generate_vultr_conf,
				self.generate_linode_conf,
				self.generate_gce_conf,
				# self.generate_scaleway_conf,
			]

		selected_gen_call = random.choice(gen_calls)

		self.log.info("Generator call: %s", selected_gen_call)
		return selected_gen_call()

	################################################################################################
	# End of config generator calls
	################################################################################################

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


	def configure_client(self, clientname, client_idx, provider=None, provider_kwargs=None):
		assert "_" not in clientname, "VM names cannot contain _ on digital ocean, I think?"
		self.log.info("Configuring client")

		commands = [
			# splat in public keys.
			['cmd.run', ['mkdir .ssh/', ],      {}],
			['cmd.run', [dirmake_ssh_oneliner, ],      {}],
			['cmd.run', ['pwd', ],      {}],
			['cmd.run', ['ls -la ', ],      {}],
			['cmd.run', ['echo ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQCoNUeZ/L6QYntVXtBCdFLk3L7X1Smio+pKi/63W4i9VQdocxY7zl3fCyu5LsPzVQUBU5n'
				+ 'LKb/iJkABH+hxq8ZL7kXiKuGgeHsI60I2wECMxg17Qs918ND626AkXqlMIUW1SchcAi3rYRMVY0OaGSOutIcjR+mJ6liogTv1DLRD0eRbuollz7XsYz4ILb'
				+ 'i9kEsqwaly92vK6vlIVlAWtDoNf95c6jk/lh0M5p1LV0lwrEtfCreuv1rrOldUdwgU4wCFgRI+p6FXs69+OsNWxZSOSr28eE9sbsHxIxthcRHMtsnDxzeJ1'
				+ 'PVhvC4JclFEHEZSlYaemI6zOezVuBuipwSv Neko@ODO | tee -a .ssh/authorized_keys', ],      {}],
			['cmd.run', ['echo ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAACAQCi7/9jOHVJj0ODnPqinqFbOaErT2pNaeq0pYKapcG2DHGrvVlX3ZUO8z7uY1QZX0OiC3y'
				+ '7rv4c7NEl7/OtmRDfNPd5YgpAuXelbwu5Pj1BjQq1pn3CeP4zhw4gcEPx2UAc5Rw1jzH8vE7NMf2iReBiHr2SfSLh8T/jt5bEAVDCnhMS/8YvoPLLftESiL'
				+ 'oi+TU6Y9/zw4zac3AyJJ02tHpHLSpWWPPLi31ASEu/p+lWynUd+dSTMbwmc3hwBQkZTrK6P1I3431eQqYVNOyWJe+GeCXLaw5CvO8qlE7Nj3Z+dics3Bq0F'
				+ '7ugDC+27qWk7m5soPfbZ8qlQz4CWFv01GHWdWwdHh9SR2bplNZ6MDuED91mu7gxyx2Wyo2AIiKsLcpGOIdLnIvrSA9VGpdgKbflbnqtfyIm6gloPpITnAJX'
				+ 'imWSvIxF76PVFjdZa86jAx7JZfBfirvtRg6/qXbDUDAErF3OllqxBvuGOzHptDDgha/29tabzxUIxhpBrG0TiRTMDmmqgM+b9kANgzEe4Yef2w/IaTC96D/'
				+ 'oLxRHmRBbof8GIMlNZjFlVw8XIyzYxnvALwCE7gRubba13f6qU0lT56be9HKYrSvHVy9/855lKlLwTCePaHK0EPBGuMWZOBexGKyxTFXmA+oqkBg5zFnZLy'
				+ 'xcsaVZQtZRnDU4Cu4jyQ== rwpscrape@fake-url.com | tee -a .ssh/authorized_keys', ],      {}],
			['cmd.run', ['echo ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAACAQDMv9sMkEOjqsFu8wPiG2jUP62qKEpxmvQ7IiYaLKogW/LQlLhKP7KCIE2MVUmctwdvyEF'
				+ 'rXGOXDCVgFMFLEZiCi2+B7itMcFBlxJsZYQ9Y5FzXg/xK/Xld9rZu2ST+4z9xrX03n0rrsvO3HgpbNoIWF1LbXrc8L80CUCf13GWkZErhzc4mcd44McLVxX'
				+ 'q+hcikMguVdOcejpLJTQkq2LRLEx2zhrz+CfNe9AQ0I5AOsh8Os3rrILFs0t290hejMX82nwJUCIcODTBJqR0o7qs/Tt8zLy3YKnAN3eGqfO7tw/d75AD/n'
				+ 'ENup5kJscpVb/6v3xfWnjgAjalj/hw2bwoc3SE+Y3u2wmyuhrJcSy6rw/IltFc+BaZamZMBW/si8tW+xo9rb903GXANJbjVOABECJSp2i03xtPfYfk9KqZb'
				+ '/vUkpYTmwRQGvDK9u1viIF8nIomE4omN6buFktvVjH1IG6bOPeMi4Y0zBNds7Q1W28Um1ygaBU+NCalep8UDEWInNkfYe1E/hj5A5EaMPaRjnPhXJqUzglO'
				+ 'l1O2Tco2FYhfvCiyZvAHv25LLrGzePidR59SzTP7/fLxK7FgmH0m79AOKvjuZaNjb7njmgDhyQggOLU6bJwiiJ7MqldPlic2qCKyQVavLv2nXGIGVXEovtM'
				+ '9YfgSYuglkiYmbs6LU0w== durr@mainnas | tee -a .ssh/authorized_keys', ],      {}],
			['cmd.run', ["chmod 0600 .ssh/authorized_keys", ],      {}],
			['cmd.run', ["cat .ssh/authorized_keys", ],      {}],
			# So something is missing some of the keys, somehow
			['cmd.run', ["eval ssh-agent $SHELL", ],      {}],
			['cmd.run', ["ssh-add .ssh/authorized_keys", ],      {}],
			['cmd.run', ["ssh-add -l", ],      {}],
			['cmd.run', ["eval ssh-agent $SHELL; ssh-add .ssh/authorized_keys; ssh-add -l", ],      {}],

			['cmd.run', [dirmake_oneliner, ],      {}],
			['cmd.run', ["apt-get update", ],      {}],
			['cmd.run', ["apt-get install -y build-essential git screen", ],      {}],
			['cmd.run', ["git clone https://github.com/fake-name/AutoTriever.git /scraper"], {}],
			['cmd.run', ["ls /scraper", ], {}],
			['cmd.run', ["whoami", ], {}],

			# Make swap so
			['cmd.run', ["dd if=/dev/zero of=/swapfile bs=1M count=1024", ], {}],
			['cmd.run', ["mkswap /swapfile", ], {}],
			['cmd.run', ["chmod 0600 /swapfile", ], {}],
			['cmd.run', ["swapon /swapfile", ], {}],

			# Needed to make GCE play nice. I think they just flat-out don't preinstall a locale
			['cmd.run', ["sudo apt-get install language-pack-en -y", ], {}],

			# Shit to make the tty work in UTF-8. Otherwise, the logging can asplode
			# and break all the things.
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


		print("Response:")
		print(resp)


		if resp[clientname] and not resp[clientname].strip().endswith('Setup OK! System is configured for launch'):
			raise VmInitError("Setup command did not return success!")

		self.log.info("Node configured! Starting scraper client!")
		jobid = self.local.cmd_async(tgt=clientname, fun='cmd.run', arg=["screen -d -m ./run.sh", ], kwarg={"cwd" : '/scraper'})
		self.log.info("Job id: '%s'", jobid)

	################################################################################################

	def make_client(self, clientname):

		provider, kwargs = self.generate_conf()
		self.log.info("Creating instance...")
		self.log.info("	Client name: '%s'", clientname)
		self.log.info("	using provider: '%s'", provider)
		self.log.info("	kwargs: '%s'", kwargs)
		try:
			ret = self.cc.create(names=[clientname], provider=provider, **kwargs)
			self.log.info("Response: %s", ret)
			self.log.info("Instance created!")
		except Exception as e:
			traceback.format_exc()
			raise marshaller_exceptions.VmCreateFailed("Failed when creating VM? Exception: %s" % e)

		return provider, kwargs

	def destroy_client(self, clientname):
		self.log.info("Destroying client named: '%s'", clientname)
		loops = 1
		nodes = [nodename for _host, nodename in self.list_nodes()]
		while clientname in nodes:
			try:
				self.log.info("Destroying %s, attempts %s", clientname, loops)
				ret = self.cc.destroy([clientname])
				self.log.info("Destroy returned: ")
				self.log.info('%s', ret)
				return
			except salt.exceptions.SaltCloudSystemExit:
				self.log.error("Failed to destroy: %s", clientname)
				for line in traceback.format_exc().split("\n"):
					self.log.error("%s", line)
			loops += 1

	################################################################################################

	def list_nodes(self):

		sources = [
			'digital_ocean',
			'vultr',
			'linode',
			'scaleway',
			'gce',
		]

		nodes = []
		countl = {}
		nodelist = self.cc.query()

		for provider in sources:
			countl.setdefault(provider, [])
			if provider in nodelist:
				if provider in nodelist[provider]:
					for key, nodedict in nodelist[provider][provider].items():
						nodes.append((provider, key))
						countl[provider].append(key)
		# Do statsd update.
		with self.mon_con.pipeline() as pipe:
			for provider in sources:
				pipe.gauge('PlatformWorkers.%s' % provider, len(countl[provider]))

		nodes.sort()
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

		for name, size_meta in sizes.items():
			if float(size_meta['price_per_month']) <= 5.0:
				print("Item:", name, size_meta)

	def list_do_options(self):
		self.log.info("DO test")
		images = self.cc.list_images(provider='digital_ocean')
		sizes = self.cc.list_sizes(provider='digital_ocean')
		pprint.pprint(images)
		pprint.pprint(sizes)


# So.... vultur support is currently fucked.
# Waiting on https://github.com/saltstack/salt/issues/37040

def vtest():
	herder = VpsHerder()

	clientname = "test-1"
	provider, kwargs = herder.generate_vultr_conf()
	herder.log.info("Creating instance...")
	herder.log.info("	Client name: '%s'", clientname)
	herder.log.info("	using provider: '%s'", provider)
	herder.log.info("	kwargs: '%s'", kwargs)
	ret = herder.cc.create(names=[clientname], provider=provider, **kwargs)
	print("Create response:", ret)

	herder.configure_client(clientname, 0, provider=provider, provider_kwargs=kwargs)
	herder.log.info("Instance created!")

def dtest():
	herder = VpsHerder()

	clientname = "test-2"
	provider, kwargs = herder.generate_do_conf()
	herder.log.info("Creating instance...")
	herder.log.info("	Client name: '%s'", clientname)
	herder.log.info("	using provider: '%s'", provider)
	herder.log.info("	kwargs: '%s'", kwargs)
	ret = herder.cc.create(names=[clientname], provider=provider, **kwargs)
	print("Create response:", ret)

	herder.configure_client(clientname, 0, provider=provider, provider_kwargs=kwargs)
	herder.log.info("Instance created!")

def ltest():
	herder = VpsHerder()

	clientname = "test-3"
	provider, kwargs = herder.generate_linode_conf()
	herder.log.info("Creating instance...")
	herder.log.info("	Client name: '%s'", clientname)
	herder.log.info("	using provider: '%s'", provider)
	herder.log.info("	kwargs: '%s'", kwargs)
	ret = herder.cc.create(names=[clientname], provider=provider, **kwargs)
	print("Create response:", ret)

	herder.configure_client(clientname, 0, provider=provider, provider_kwargs=kwargs)
	herder.log.info("Instance created!")

def stest():
	herder = VpsHerder()

	clientname = "test-4"
	provider, kwargs = herder.generate_scaleway_conf()
	herder.log.info("Creating instance...")
	herder.log.info("	Client name: '%s'", clientname)
	herder.log.info("	using provider: '%s'", provider)
	herder.log.info("	kwargs: '%s'", kwargs)
	ret = herder.cc.create(names=[clientname], provider=provider, **kwargs)
	print("Create response:", ret)

	herder.configure_client(clientname, 0, provider=provider, provider_kwargs=kwargs)
	herder.log.info("Instance created!")



def gtest():
	herder = VpsHerder()

	clientname = "test-5"
	provider, kwargs = herder.generate_gce_conf()
	herder.log.info("Creating instance...")
	herder.log.info("	Client name: '%s'", clientname)
	herder.log.info("	using provider: '%s'", provider)
	herder.log.info("	kwargs: '%s'", kwargs)
	ret = herder.cc.create(names=[clientname], provider=provider, **kwargs)
	print("Create response:", ret)

	herder.configure_client(clientname, 0, provider=provider, provider_kwargs=kwargs)
	herder.log.info("Instance created!")

def destroy_all():
	herder = VpsHerder()

	while [node for host, node in herder.list_nodes() if 'scrape-worker' in node]:
		for node in [node for host, node in herder.list_nodes() if 'scrape-worker' in node]:
			print("Destroy call for node: '%s'" % node)
			herder.destroy_client(node)

def destroy():
	herder = VpsHerder()

	bad = ["test-1", "test-2", "test-3", "test-4", "test-5"]
	for badname in bad:
		try:
			herder.destroy_client(badname)
		except Exception:
			traceback.print_exc()
			print("Continuing")

def list_nodes():
	herder = VpsHerder()
	nodes = herder.list_nodes()
	print("Active nodes:")
	for node in nodes:
		print("	" + str(node))


def list_vultr_options():
	herder = VpsHerder()
	herder.list_vultr_options()

def list_do_options():
	herder = VpsHerder()
	herder.list_do_options()


def list_gce_options():
	herder = VpsHerder()
	meta = herder.generate_gce_conf()
	print(meta)

def brute_vtest():
	herder = VpsHerder()
	while 1:
		vtest()
		herder.destroy_client("test-1")

def brute_dtest():
	herder = VpsHerder()
	while 1:
		dtest()
		herder.destroy_client("test-1")

def configure():
	herder = VpsHerder()
	herder.configure_client("test-1", 0)

def test_1():
	herder = VpsHerder()
	herder.make_client("test-1")
	herder.configure_client("test-1", 0)

def gen_call():
	herder = VpsHerder()
	conf = herder.generate_conf()
	print("Generated configuration:")
	print(conf)



def go():

	cmd_args = [tmp for tmp in sys.argv]
	if "-v" in cmd_args:
		cmd_args.remove("-v")
		logSetup.initLogging(logLevel=logging.DEBUG)
	else:
		logSetup.initLogging()

	fmap = {

		"vtest" : vtest,
		"ltest" : ltest,
		"stest" : stest,
		"dtest" : dtest,
		"gtest" : gtest,

		"destroy"     : destroy,
		'destroy-all' : destroy_all,
		"list"        : list_nodes,
		"vultr-opts"  : list_vultr_options,
		"do-opts"     : list_do_options,
		"gce-opts"    : list_gce_options,


		 "brute-vtest" : brute_vtest,
		 "brute-dtest" : brute_dtest,
		 "configure"   : configure,
		 'test-1'      : test_1,
		 "gen-call"    : gen_call,


	}


	if len(cmd_args) == 1:
		print("Nothing to do")
		print("Available options:")
		for key in fmap.keys():
			print("	" + key)
		return

	command = cmd_args[1]

	if command in fmap:
		print("executing command %s for arg '%s'" % (fmap[command], command))
		fmap[command]()
		return
	else:
		print("Error! Unknown command line arg: '%s'" % command)



if __name__ == '__main__':
	go()
