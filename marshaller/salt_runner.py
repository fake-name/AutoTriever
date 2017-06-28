

import sys
import pprint
import random
import logging
import json
import copy
import traceback
import uuid
import ast

import settings

import salt.cloud
import salt.exceptions
import salt.client
import salt.config
import salt.exceptions

import marshaller_exceptions
import logSetup
import os.path

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




	def get_5_dollar_do_meta(self):
		self.log.info("Generating DO Configuration")

		sizes = self.cc.list_sizes(provider='do')['do']['digital_ocean']
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

		provider = "do"
		kwargs = {
			'image': 'ubuntu-14-04-x64',
			'size': planid,
			# 'vm_size': planid,
			'private_networking' : False,
			'location' : place,
		}

		return provider, kwargs

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


		}
		return provider, kwargs


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


		}
		return provider, kwargs



	def generate_conf(self):
		# TODO: Vultr goes here too
		return random.choice([
				self.generate_do_conf,
				self.generate_vultr_conf,
				# self.generate_linode_conf,
				# self.generate_scaleway_conf,
			])()
		# return random.choice([self.generate_do_conf])()
		gen_call = random.choice([self.generate_do_conf, self.generate_vultr_conf])
		self.log.info("Generator call: %s", gen_call)
		return gen_call()

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
			raise marshaller_exceptions.VmCreateFailed("Failed when creating VM? Exception: %s" % e)
		# instance = cc.create(names=['test-1'], provider=provider, **kwargs)
		# print(ret)


	def configure_client(self, clientname, client_idx):
		assert "_" not in clientname, "VM names cannot contain _ on digital ocean, I think?"
		self.log.info("Configuring client")

		commands = [
			# splat in public keys.
			['cmd.run', ['mkdir -p ~/.ssh/', ],      {}],
			['cmd.run', ['echo ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQCoNUeZ/L6QYntVXtBCdFLk3L7X1Smio+pKi/63W4i9VQdocxY7zl3fCyu5LsPzVQUBU5n'
				+ 'LKb/iJkABH+hxq8ZL7kXiKuGgeHsI60I2wECMxg17Qs918ND626AkXqlMIUW1SchcAi3rYRMVY0OaGSOutIcjR+mJ6liogTv1DLRD0eRbuollz7XsYz4ILb'
				+ 'i9kEsqwaly92vK6vlIVlAWtDoNf95c6jk/lh0M5p1LV0lwrEtfCreuv1rrOldUdwgU4wCFgRI+p6FXs69+OsNWxZSOSr28eE9sbsHxIxthcRHMtsnDxzeJ1'
				+ 'PVhvC4JclFEHEZSlYaemI6zOezVuBuipwSv Neko@ODO | tee -a ~/.ssh/authorized_keys', ],      {}],
			['cmd.run', ['echo ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAACAQCi7/9jOHVJj0ODnPqinqFbOaErT2pNaeq0pYKapcG2DHGrvVlX3ZUO8z7uY1QZX0OiC3y'
				+ '7rv4c7NEl7/OtmRDfNPd5YgpAuXelbwu5Pj1BjQq1pn3CeP4zhw4gcEPx2UAc5Rw1jzH8vE7NMf2iReBiHr2SfSLh8T/jt5bEAVDCnhMS/8YvoPLLftESiL'
				+ 'oi+TU6Y9/zw4zac3AyJJ02tHpHLSpWWPPLi31ASEu/p+lWynUd+dSTMbwmc3hwBQkZTrK6P1I3431eQqYVNOyWJe+GeCXLaw5CvO8qlE7Nj3Z+dics3Bq0F'
				+ '7ugDC+27qWk7m5soPfbZ8qlQz4CWFv01GHWdWwdHh9SR2bplNZ6MDuED91mu7gxyx2Wyo2AIiKsLcpGOIdLnIvrSA9VGpdgKbflbnqtfyIm6gloPpITnAJX'
				+ 'imWSvIxF76PVFjdZa86jAx7JZfBfirvtRg6/qXbDUDAErF3OllqxBvuGOzHptDDgha/29tabzxUIxhpBrG0TiRTMDmmqgM+b9kANgzEe4Yef2w/IaTC96D/'
				+ 'oLxRHmRBbof8GIMlNZjFlVw8XIyzYxnvALwCE7gRubba13f6qU0lT56be9HKYrSvHVy9/855lKlLwTCePaHK0EPBGuMWZOBexGKyxTFXmA+oqkBg5zFnZLy'
				+ 'xcsaVZQtZRnDU4Cu4jyQ== rwpscrape@fake-url.com | tee -a ~/.ssh/authorized_keys', ],      {}],
			['cmd.run', ['echo ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAACAQDMv9sMkEOjqsFu8wPiG2jUP62qKEpxmvQ7IiYaLKogW/LQlLhKP7KCIE2MVUmctwdvyEF'
				+ 'rXGOXDCVgFMFLEZiCi2+B7itMcFBlxJsZYQ9Y5FzXg/xK/Xld9rZu2ST+4z9xrX03n0rrsvO3HgpbNoIWF1LbXrc8L80CUCf13GWkZErhzc4mcd44McLVxX'
				+ 'q+hcikMguVdOcejpLJTQkq2LRLEx2zhrz+CfNe9AQ0I5AOsh8Os3rrILFs0t290hejMX82nwJUCIcODTBJqR0o7qs/Tt8zLy3YKnAN3eGqfO7tw/d75AD/n'
				+ 'ENup5kJscpVb/6v3xfWnjgAjalj/hw2bwoc3SE+Y3u2wmyuhrJcSy6rw/IltFc+BaZamZMBW/si8tW+xo9rb903GXANJbjVOABECJSp2i03xtPfYfk9KqZb'
				+ '/vUkpYTmwRQGvDK9u1viIF8nIomE4omN6buFktvVjH1IG6bOPeMi4Y0zBNds7Q1W28Um1ygaBU+NCalep8UDEWInNkfYe1E/hj5A5EaMPaRjnPhXJqUzglO'
				+ 'l1O2Tco2FYhfvCiyZvAHv25LLrGzePidR59SzTP7/fLxK7FgmH0m79AOKvjuZaNjb7njmgDhyQggOLU6bJwiiJ7MqldPlic2qCKyQVavLv2nXGIGVXEovtM'
				+ '9YfgSYuglkiYmbs6LU0w== durr@mainnas | tee -a ~/.ssh/authorized_keys', ],      {}],

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

		# images = cc.list_images(provider='scaleway')
		# locs   = cc.list_locations(provider='scaleway')
		# sizes  = cc.list_sizes(provider='scaleway')
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
		if 'linode' in nodelist:
			if 'linode' in nodelist['linode']:
				for key, nodedict in nodelist['linode']['linode'].items():
					if key:
						nodes.append(key.encode("ascii"))
		if 'scaleway' in nodelist:
			if 'scaleway' in nodelist['scaleway']:
				for key, nodedict in nodelist['scaleway']['scaleway'].items():
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

		for name, size_meta in sizes.items():
			if float(size_meta['price_per_month']) <= 5.0:
				print("Item:", name, size_meta)

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

	herder.configure_client(clientname, 0)
	herder.log.info("Instance created!")

def dtest():
	clientname = "test-2"
	provider, kwargs = herder.generate_do_conf()
	herder.log.info("Creating instance...")
	herder.log.info("	Client name: '%s'", clientname)
	herder.log.info("	using provider: '%s'", provider)
	herder.log.info("	kwargs: '%s'", kwargs)
	ret = herder.cc.create(names=[clientname], provider=provider, **kwargs)
	print("Create response:", ret)

	herder.configure_client(clientname, 0)
	herder.log.info("Instance created!")

def ltest():
	clientname = "test-3"
	provider, kwargs = herder.generate_linode_conf()
	herder.log.info("Creating instance...")
	herder.log.info("	Client name: '%s'", clientname)
	herder.log.info("	using provider: '%s'", provider)
	herder.log.info("	kwargs: '%s'", kwargs)
	ret = herder.cc.create(names=[clientname], provider=provider, **kwargs)
	print("Create response:", ret)

	herder.configure_client(clientname, 0)
	herder.log.info("Instance created!")

def stest():
	clientname = "test-4"
	provider, kwargs = herder.generate_scaleway_conf()
	herder.log.info("Creating instance...")
	herder.log.info("	Client name: '%s'", clientname)
	herder.log.info("	using provider: '%s'", provider)
	herder.log.info("	kwargs: '%s'", kwargs)
	ret = herder.cc.create(names=[clientname], provider=provider, **kwargs)
	print("Create response:", ret)

	herder.configure_client(clientname, 0)
	herder.log.info("Instance created!")



if __name__ == '__main__':
	logSetup.initLogging()
	herder = VpsHerder()


	if "vtest" in sys.argv:
		vtest()
	elif "ltest" in sys.argv:
		ltest()
	elif "dtest" in sys.argv:
		dtest()
	elif "stest" in sys.argv:
		stest()
	elif "destroy-all" in sys.argv:
		while herder.list_nodes():
			for node in herder.list_nodes():
				herder.destroy_client(node)
	elif "destroy" in sys.argv:
		bad = ["test-1", "test-2", "test-3", "test-4"]
		for badname in bad:
			try:
				herder.destroy_client(badname)
			except Exception:
				traceback.print_exc()
				print("Continuing")
	elif "brute-vtest" in sys.argv:
		while 1:
			vtest()
			herder.destroy_client("test-1")
	elif "brute-dtest" in sys.argv:
		while 1:
			dtest()
			herder.destroy_client("test-1")
	elif "vtest" in sys.argv:
		vtest()
		herder.destroy_client("test-1")
	elif "dtest" in sys.argv:
		dtest()
		herder.destroy_client("test-1")
	elif "list" in sys.argv:
		herder.list_nodes()
	elif "configure" in sys.argv:
		herder.configure_client("test-1", 0)
	elif 'test-1' in sys.argv:
		herder.make_client("test-1")
		herder.configure_client("test-1", 0)
	elif "vultr-opts" in sys.argv:
		herder.list_vultr_options()
	elif "do-opts" in sys.argv:
		herder.list_do_options()
	elif "gen-call" in sys.argv:
		conf = herder.generate_conf()
		print("Generated configuration:")
		print(conf)
	else:
		print("Nothing to do")
