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
import math
import datetime
# import tornado.ioloop


def gen_random_string(length):
	if not hasattr(gen_random_string, "rng"):
		gen_random_string.rng = random.SystemRandom() # Create a static variable
	return ''.join([ gen_random_string.rng.choice(string.ascii_letters + string.digits) for _ in range(length) ])

def weighted_choice(weights):
	totals = []
	running_total = 0

	for w in weights:
		running_total += w
		totals.append(running_total)

	rnd = random.random() * running_total
	for i, total in enumerate(totals):
		if rnd < total:
			return i

def generate_weights(length, time_override=None):
	if time_override:
		now = time_override
	else:
		now = datetime.datetime.utcnow()
	seconds_since_midnight = (now - now.replace(hour=0, minute=0, second=0, microsecond=0)).total_seconds()
	day_fraction = seconds_since_midnight / 86400

	day_angle = day_fraction * 2 * math.pi

	weights = []
	for x in range(length):
		ang = x * ((2 * math.pi) / length) + day_angle

		weight = math.sin(ang)
		weight += 1
		weights.append(weight)

	return weights


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

	"threads"  : 10,

	'captcha_solvers' : {}

}

class VmInitError(RuntimeError):
	pass

dirmake_ssh_oneliner = 'python -c \'import os.path, sys, os; os.makedirs(".ssh/") if not os.path.exists(".ssh/") else None; print("Dir exists and is dir: ", os.path.isdir(".ssh/"));sys.exit(1 if os.path.isdir(".ssh/") else 0);\''
dirmake_oneliner = 'python -c \'import os.path, sys, os; os.makedirs("/scraper") if not os.path.exists("/scraper") else None; print("Dir exists and is dir: ", os.path.isdir("/scraper"));sys.exit(1 if os.path.isdir("/scraper") else 0);\''

class VpsHerder(object):

	def __init__(self, debug=False):


		self.debug = debug
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

		# self.io_loop = tornado.ioloop.IOLoop()


	################################################################################################
	# Digital Ocean
	################################################################################################

	def get_5_dollar_do_meta(self):
		self.log.info("Generating DO Configuration")

		sizes = self.cc.list_sizes(provider='digitalocean')['digitalocean']['digitalocean']
		locs = self.cc.list_locations(provider='digitalocean')['digitalocean']['digitalocean']
		images = self.cc.list_images(provider='digitalocean')['digitalocean']['digitalocean']

		im = images['18.04 (LTS) x64']

		self.log.info("Found %s sizes, %s locations", len(sizes), len(locs))
		items = []

		avail_im_locs = set(im['regions'])
		avail_hw_locs = {}

		for name, loc_meta in locs.items():
			if loc_meta['available']:
				# Why the fuck is this a string?
				if isinstance(loc_meta['sizes'], str):
					loc_meta['sizes'] = ast.literal_eval(loc_meta['sizes'])
				if isinstance(loc_meta['sizes'], list):
					avail_hw_locs.setdefault(loc_meta['slug'], set())
					for size in loc_meta['sizes']:
						avail_hw_locs[loc_meta['slug']].add(size)

		for name, size_meta in sizes.items():
			if float(size_meta['price_monthly']) <= MAX_MONTHLY_PRICE_DOLLARS:

				# Skip 512 mb configurations (they fail setup)
				if int(size_meta['memory']) < 1000:
					continue

				# Why the fuck is this a string?
				if isinstance(size_meta['regions'], str):
					size_meta['regions'] = ast.literal_eval(size_meta['regions'])

				for loc in size_meta['regions']:
					if loc in avail_im_locs and loc in avail_hw_locs:
						if name in avail_hw_locs[loc]:
							items.append((name, loc))


		self.log.info("Found %s potential VPS location/configurations", len(items))
		return random.choice(items)

	def generate_do_conf(self):

		try:
			planid, place = self.get_5_dollar_do_meta()
		except TypeError as e:
			raise  marshaller_exceptions.VmCreateFailed("Failed when generating VM configuration? Exception: %s" % e)

		scriptname = "bootstrap-salt-delay.sh"
		scriptdir  = os.path.dirname(os.path.realpath(__file__))
		fqscript = os.path.join(scriptdir, scriptname)

		provider = "digitalocean"
		kwargs = {
			'image': 'ubuntu-18-04-x64',
			'size': planid,
			# 'vm_size': planid,
			'private_networking' : False,
			'location' : place,

			'script'             : fqscript,
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
			raise  marshaller_exceptions.VmCreateFailed("Failed when generating VM configuration? Exception: %s" % e)

		if not planid:
			raise marshaller_exceptions.VmCreateFailed("No vultr plan available?")

		scriptname = "bootstrap-salt-delay.sh"
		scriptdir  = os.path.dirname(os.path.realpath(__file__))
		fqscript = os.path.join(scriptdir, scriptname)

		kwargs = {
			'image'              : 'Ubuntu 18.04 x64',
			'private_networking' : False,
			'size'               : planid,
			'location'           : place,

			'script'             : fqscript,
			# 'script_args'        : "-D",
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
			if size_meta[u'price']['monthly'] <= 5:
				sizel.append(name)


		for name, _ in locations.items():
			locl.append(name)

		self.log.info("Found %s potential linode locations, %s sizes", len(locl), len(sizel))

		return sizel, locl

	def generate_linode_conf(self):

		provider = "linode"

		plans, places = self.get_linode_5_bux_meta()

		scriptname = "bootstrap-salt-delay.sh"
		scriptdir  = os.path.dirname(os.path.realpath(__file__))
		fqscript = os.path.join(scriptdir, scriptname)

		kwargs = {
			# 'image'              : 'Ubuntu 18.04 x64',
			# 'private_networking' : False,
			# 'size'               : planid,
			# 'location'           : random.choice(places),

			'size'     : random.choice(plans),
			'image'    : u'linode/ubuntu18.04',
			'location' : random.choice(places),

			'script'             : fqscript,
			# 'script_args'        : "-D",

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

		gce_images = self.cc.list_images(provider='gce')


		images = gce_images['gce']['gce']

		image = None
		for key in images:
			if key.startswith('ubuntu-1804-xenial-'):
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
			raise VmInitError("No Ubuntu 18.04 image found!")

		scriptname = "bootstrap-salt-delay.sh"
		scriptdir  = os.path.dirname(os.path.realpath(__file__))
		fqscript = os.path.join(scriptdir, scriptname)

		kwargs = {
			# 'image'              : 'Ubuntu 18.04 x64',
			# 'private_networking' : False,
			# 'size'               : planid,
			# 'location'           : random.choice(places),

			'size'     : size,
			'image'    : image,
			'location' : random.choice(places),

			'script'             : fqscript,
			# 'script_args'        : "-D",

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
			# 'image'              : 'Ubuntu 18.04 x64',
			# 'private_networking' : False,
			# 'size'               : planid,
			# 'location'           : random.choice(places),

			'size'     : size,
			'image'    : u'Ubuntu Xenial (18.04 latest)',
			'location' : location,

			'script'             : fqscript,
			# 'script_args'        : "-D",

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
				self.generate_do_conf,
				# self.generate_vultr_conf,
				self.generate_vultr_conf,
				self.generate_linode_conf,
				self.generate_linode_conf,
				# self.generate_gce_conf,
				# self.generate_gce_conf,
				# self.generate_scaleway_conf,
			]

		weights = generate_weights(len(gen_calls))
		print("Generated weighting:", weights)
		selected_gen_call = gen_calls[weighted_choice(weights)]

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

		conf['captcha_solvers'] = settings.CAPTCHA

		return json.dumps(conf)

	def validate_expect(self, resp, expect):
		# Print as a tuple, so literal "\n"s don't produde line-breaks in the log output
		self.log.info("Response: %s", (resp, ))

		assert isinstance(expect, list), "Expect must be a list!"

		for expect_val in expect:
			if isinstance(expect_val, str):
				if isinstance(resp, bool):
					if self.debug:
						import pdb
						pdb.set_trace()
					raise marshaller_exceptions.InvalidDeployResponse("Expected '%s' response: '%s'" % (expect_val, resp))

				elif isinstance(resp, str):
					if not expect_val in resp:
						if self.debug:
							import pdb
							pdb.set_trace()
						raise marshaller_exceptions.InvalidDeployResponse("Expected '%s' in response '%s'" % (expect_val, resp))
					else:
						self.log.info("Found %s in response!", expect)

				elif isinstance(resp, dict):
					if not expect_val in str(resp):
						if self.debug:
							import pdb
							pdb.set_trace()
						raise marshaller_exceptions.InvalidDeployResponse("Expected '%s' in response '%s'" % (expect_val, resp))
					else:
						self.log.info("Found %s in response!", expect)

				else:
					self.log.error("Unknown response type: %s!", type(resp))
			else:
				self.log.error("Unknown expect type: %s!", type(resp))
				# if self.debug:
				# 	import pdb
				# 	pdb.set_trace()
				raise marshaller_exceptions.InvalidExpectParameter("Invalid expect parameter: '%s' (type: %s)." % (expect_val, type(expect_val)))

		self.log.info("Command response passed validation.")

	def configure_client(self, clientname, client_idx, provider=None, provider_kwargs=None):
		assert "_" not in clientname, "VM names cannot contain _ on digital ocean, I think?"
		self.log.info("Configuring client")


		# [Command, [shell command], {execution context}, ['strings', 'expected', 'in', 'response']],
		commands = [
			['cmd.run', ["bash -c \'whoami\'", ],                                                                                                 {}, ['root']],
			['cmd.run', ['mkdir -p .ssh/', ],                                                                                                     {}, None],
			['cmd.run', [dirmake_oneliner, ],                                                                                                     {}, None],
			['cmd.run', [dirmake_ssh_oneliner, ],                                                                                                 {}, None],
			['cmd.run', ["bash -c \"ls /\"", ],                                                                                                   {}, ['scraper', ]],
			['cmd.run', ['bash -c \"pwd\"', ],                                                                                                    {}, ['/root']],
			['cmd.run', ['bash -c \"ls -la\"', ],                                                                                                 {}, None],
			['pkg.refresh_db', [],                                                                                                                {}, None],
			['pkg.install', ['software-properties-common', ],                                                                                     {}, None],

			# splat in public keys.
			['cmd.run', ['echo ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQCoNUeZ/L6QYntVXtBCdFLk3L7X1Smio+pKi/63W4i9VQdocxY7zl3fCyu5LsPzVQUBU5n'
				+ 'LKb/iJkABH+hxq8ZL7kXiKuGgeHsI60I2wECMxg17Qs918ND626AkXqlMIUW1SchcAi3rYRMVY0OaGSOutIcjR+mJ6liogTv1DLRD0eRbuollz7XsYz4ILb'
				+ 'i9kEsqwaly92vK6vlIVlAWtDoNf95c6jk/lh0M5p1LV0lwrEtfCreuv1rrOldUdwgU4wCFgRI+p6FXs69+OsNWxZSOSr28eE9sbsHxIxthcRHMtsnDxzeJ1'
				+ 'PVhvC4JclFEHEZSlYaemI6zOezVuBuipwSv Neko@ODO | tee -a .ssh/authorized_keys', ],                                                {}, None],
			['cmd.run', ['echo ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAACAQCi7/9jOHVJj0ODnPqinqFbOaErT2pNaeq0pYKapcG2DHGrvVlX3ZUO8z7uY1QZX0OiC3y'
				+ '7rv4c7NEl7/OtmRDfNPd5YgpAuXelbwu5Pj1BjQq1pn3CeP4zhw4gcEPx2UAc5Rw1jzH8vE7NMf2iReBiHr2SfSLh8T/jt5bEAVDCnhMS/8YvoPLLftESiL'
				+ 'oi+TU6Y9/zw4zac3AyJJ02tHpHLSpWWPPLi31ASEu/p+lWynUd+dSTMbwmc3hwBQkZTrK6P1I3431eQqYVNOyWJe+GeCXLaw5CvO8qlE7Nj3Z+dics3Bq0F'
				+ '7ugDC+27qWk7m5soPfbZ8qlQz4CWFv01GHWdWwdHh9SR2bplNZ6MDuED91mu7gxyx2Wyo2AIiKsLcpGOIdLnIvrSA9VGpdgKbflbnqtfyIm6gloPpITnAJX'
				+ 'imWSvIxF76PVFjdZa86jAx7JZfBfirvtRg6/qXbDUDAErF3OllqxBvuGOzHptDDgha/29tabzxUIxhpBrG0TiRTMDmmqgM+b9kANgzEe4Yef2w/IaTC96D/'
				+ 'oLxRHmRBbof8GIMlNZjFlVw8XIyzYxnvALwCE7gRubba13f6qU0lT56be9HKYrSvHVy9/855lKlLwTCePaHK0EPBGuMWZOBexGKyxTFXmA+oqkBg5zFnZLy'
				+ 'xcsaVZQtZRnDU4Cu4jyQ== rwpscrape@fake-url.com | tee -a .ssh/authorized_keys', ],                                               {}, None],
			['cmd.run', ['echo ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAACAQDMv9sMkEOjqsFu8wPiG2jUP62qKEpxmvQ7IiYaLKogW/LQlLhKP7KCIE2MVUmctwdvyEF'
				+ 'rXGOXDCVgFMFLEZiCi2+B7itMcFBlxJsZYQ9Y5FzXg/xK/Xld9rZu2ST+4z9xrX03n0rrsvO3HgpbNoIWF1LbXrc8L80CUCf13GWkZErhzc4mcd44McLVxX'
				+ 'q+hcikMguVdOcejpLJTQkq2LRLEx2zhrz+CfNe9AQ0I5AOsh8Os3rrILFs0t290hejMX82nwJUCIcODTBJqR0o7qs/Tt8zLy3YKnAN3eGqfO7tw/d75AD/n'
				+ 'ENup5kJscpVb/6v3xfWnjgAjalj/hw2bwoc3SE+Y3u2wmyuhrJcSy6rw/IltFc+BaZamZMBW/si8tW+xo9rb903GXANJbjVOABECJSp2i03xtPfYfk9KqZb'
				+ '/vUkpYTmwRQGvDK9u1viIF8nIomE4omN6buFktvVjH1IG6bOPeMi4Y0zBNds7Q1W28Um1ygaBU+NCalep8UDEWInNkfYe1E/hj5A5EaMPaRjnPhXJqUzglO'
				+ 'l1O2Tco2FYhfvCiyZvAHv25LLrGzePidR59SzTP7/fLxK7FgmH0m79AOKvjuZaNjb7njmgDhyQggOLU6bJwiiJ7MqldPlic2qCKyQVavLv2nXGIGVXEovtM'
				+ '9YfgSYuglkiYmbs6LU0w== durr@mainnas | tee -a .ssh/authorized_keys', ],                                                         {}, None],
			['cmd.run', ["chmod 0600 .ssh/authorized_keys", ],                                                                                    {}, None],
			['cmd.run', ["cat .ssh/authorized_keys", ],                                                                                           {}, [' Neko@ODO', ' rwpscrape@fake-url.com', ' durr@mainnas', ]],
			# So something is missing some of the keys, somehow
			['cmd.run', ["eval ssh-agent $SHELL", ],                                                                                              {}, None],
			['cmd.run', ["ssh-add .ssh/authorized_keys", ],                                                                                       {}, None],
			['cmd.run', ["ssh-add -l", ],                                                                                                         {}, None],
			['cmd.run', ["eval ssh-agent $SHELL; ssh-add .ssh/authorized_keys; ssh-add -l", ],                                                    {}, None],

			['cmd.run', ["apt-get update", ],                                                                                                     {}, None],

			# So trying to have salt update itself makes it poop itself,
			# and never come back.
			# Siiiiiigh.
			# Anyways, I moved this command to my custom bootstrap script.
			# ['cmd.run', ["apt-get dist-upgrade -y", ],                                                                                            {'env' : {'DEBIAN_FRONTEND' : 'noninteractive'}}, None],

			# Apparently at least one VPS host has separated git from build-essential?
			# ['pkg.install', ['build-essential', 'locales', 'git', 'libfontconfig', 'wget', 'htop', 'libxml2', 'libxslt1-dev',
			# 	'python3-dev', 'python3-dbg', 'python3-distutils', 'libz-dev', 'curl', 'screen'],                                                                      {}, None],
			# ['pkg.install', ['libasound2', 'libatk1.0-0', 'libc6', 'libcairo2', 'libcups2', 'libdbus-1-3', 'libexpat1', 'libfontconfig1', 'libgcc1',
			# 		'libgconf-2-4', 'libgdk-pixbuf2.0-0', 'libglib2.0-0', 'libgtk-3-0', 'libnspr4', 'libpango-1.0-0', 'libpangocairo-1.0-0', 'libstdc++6',
			# 		'libx11-6', 'libx11-xcb1', 'libxcb1', 'libxcursor1', 'libxdamage1', 'libxext6', 'libxfixes3', 'libxi6', 'libxrandr2', 'libxrender1',
			# 		'libxss1', 'libxtst6', 'libnss3'],                                                                                            {}, None],

			['pkg.install', ['build-essential', ],                                                                                                {}, None],
			['pkg.install', ['locales', ],                                                                                                        {}, None],
			['pkg.install', ['git', ],                                                                                                            {}, None],
			['pkg.install', ['libfontconfig', ],                                                                                                  {}, None],
			['pkg.install', ['wget', ],                                                                                                           {}, None],
			['pkg.install', ['htop', ],                                                                                                           {}, None],
			['pkg.install', ['libxml2', ],                                                                                                        {}, None],
			['pkg.install', ['libxslt1-dev',],                                                                                                    {}, None],
			['pkg.install', ['python3-dev', ],                                                                                                    {}, None],
			['pkg.install', ['python3-dbg', ],                                                                                                    {}, None],
			['pkg.install', ['python3-distutils', ],                                                                                              {}, None],
			['pkg.install', ['libz-dev', ],                                                                                                       {}, None],
			['pkg.install', ['curl', ],                                                                                                           {}, None],
			['pkg.install', ['screen'],                                                                                                           {}, None],
			['pkg.install', ['libasound2', ],                                                                                                     {}, None],
			['pkg.install', ['libatk1.0-0', ],                                                                                                    {}, None],
			['pkg.install', ['libc6', ],                                                                                                          {}, None],
			['pkg.install', ['libcairo2', ],                                                                                                      {}, None],
			['pkg.install', ['libcups2', ],                                                                                                       {}, None],
			['pkg.install', ['libdbus-1-3', ],                                                                                                    {}, None],
			['pkg.install', ['libexpat1', ],                                                                                                      {}, None],
			['pkg.install', ['libfontconfig1', ],                                                                                                 {}, None],
			['pkg.install', ['libgcc1',],                                                                                                         {}, None],
			['pkg.install', ['libgconf-2-4', ],                                                                                                   {}, None],
			['pkg.install', ['libgdk-pixbuf2.0-0', ],                                                                                             {}, None],
			['pkg.install', ['libglib2.0-0', ],                                                                                                   {}, None],
			['pkg.install', ['libgtk-3-0', ],                                                                                                     {}, None],
			['pkg.install', ['libnspr4', ],                                                                                                       {}, None],
			['pkg.install', ['libpango-1.0-0', ],                                                                                                 {}, None],
			['pkg.install', ['libpangocairo-1.0-0', ],                                                                                            {}, None],
			['pkg.install', ['libstdc++6',],                                                                                                      {}, None],
			['pkg.install', ['libx11-6', ],                                                                                                       {}, None],
			['pkg.install', ['libx11-xcb1', ],                                                                                                    {}, None],
			['pkg.install', ['libxcb1', ],                                                                                                        {}, None],
			['pkg.install', ['libxcursor1', ],                                                                                                    {}, None],
			['pkg.install', ['libxdamage1', ],                                                                                                    {}, None],
			['pkg.install', ['libxext6', ],                                                                                                       {}, None],
			['pkg.install', ['libxfixes3', ],                                                                                                     {}, None],
			['pkg.install', ['libxi6', ],                                                                                                         {}, None],
			['pkg.install', ['libxrandr2', ],                                                                                                     {}, None],
			['pkg.install', ['libxrender1',],                                                                                                     {}, None],
			['pkg.install', ['libxss1', ],                                                                                                        {}, None],
			['pkg.install', ['libxtst6', ],                                                                                                       {}, None],
			['pkg.install', ['libnss3'],                                                                                                          {}, None],
			['pkg.install', ["xvfb", ],                                                                                                           {}, None],

			# Adblocking. Lower the chrome cpu costs decently
			# So long hosts files cause things to explode, so we turn it off.
			# ['cmd.run', ["curl https://raw.githubusercontent.com/StevenBlack/hosts/master/alternates/social/hosts | tee -a /etc/hosts", ],        {}, None],

			# Make swap so
			['cmd.run', ["dd if=/dev/zero of=/swapfile bs=1M count=4096", ],                                                                      {}, None],
			['cmd.run', ["mkswap /swapfile", ],                                                                                                   {}, None],
			['cmd.run', ["chmod 0600 /swapfile", ],                                                                                               {}, None],
			['cmd.run', ["swapon /swapfile", ],                                                                                                   {}, None],
			['cmd.run', ['echo "/swapfile swap swap defaults 0 0" | sudo tee -a /etc/fstab', ],                                                   {}, None],
			['cmd.run', ["bash -c \"ls /\"", ],                                                                                                   {}, ['swapfile', ]],
			['cmd.run', ["bash -c \"cat /etc/fstab /\"", ],                                                                                       {}, ['swapfile', ]],

			# Needed to make GCE play nice. I think they just flat-out don't preinstall a locale
			# ['cmd.run', ["sudo apt-get install language-pack-en -y", ],                                                                           {}, ['The following NEW packages will be installed:', 'language-pack-en-base']],

			# Shit to make the tty work in UTF-8. Otherwise, the logging can asplode
			# and break all the things.
			['cmd.run', ['echo LANG=\"en_US.UTF-8\"   >> /etc/default/locale', ],                                                                 {}, None],
			['cmd.run', ['echo LC_ALL=\"en_US.UTF-8\" >> /etc/default/locale', ],                                                                 {}, None],
			['cmd.run', ['echo "LC_ALL=en_US.UTF-8"   >> /etc/environment', ],                                                                    {}, None],
			['cmd.run', ['echo "en_US.UTF-8 UTF-8"    >> /etc/locale.gen', ],                                                                     {}, None],
			['cmd.run', ['echo "LANG=en_US.UTF-8"     > /etc/locale.conf', ],                                                                     {}, None],
			['cmd.run', ["dpkg-reconfigure -f noninteractive locales", ],                                                                         {}, ['en_US.UTF-8']],
			['cmd.run', ["locale", ],                                                                                                             {}, None],
			['cmd.run', ["bash -c \"locale\"", ],                                                                                                 {}, None],


			# Clone and Install settings
			['cmd.run', ["bash -c \"ls /\"", ],                                                                                                   {}, ['scraper', ]],
			['cmd.run', ["git clone https://github.com/fake-name/AutoTriever.git /scraper"],                                                      {}, []],
			['cmd.run', ["cat << EOF > /scraper/settings.json \n{content}\nEOF".format(content=self.__make_conf_file(clientname, client_idx)), ], {}, None],

			# Make sure it all checked out at least somewhat
			['cmd.run', ["bash -c \"ls /scraper\"", ],                                                                                            {}, ['configure.sh', 'run.sh', 'settings.json']],

			# Finally, run the thing

			['cmd.run', ["adduser scrapeworker --disabled-password --gecos \"\"", ],                                                                           {}, ["Adding user `scrapeworker'"]],
			['cmd.run', ["usermod -a -G sudo scrapeworker", ],                                                                                    {}, None],
			['cmd.run', ["echo 'scrapeworker ALL=(ALL) NOPASSWD: ALL' | tee -a /etc/sudoers", ],                                                  {}, None],

			['cmd.run', ["wget https://raw.githubusercontent.com/solarkennedy/instant-py-bt/master/py-bt -O /usr/local/bin/py-bt", ],             {}, None],
			['cmd.run', ["wget https://raw.githubusercontent.com/aurora/rmate/master/rmate -O /usr/local/bin/rmate", ],                           {}, None],
			['cmd.run', ["chmod +x /usr/local/bin/py-bt", ],                                                                                      {}, None],
			['cmd.run', ["chmod +x /usr/local/bin/rmate", ],                                                                                      {}, None],

			['cmd.run', ["chown -R scrapeworker:scrapeworker /scraper", ],                                                                        {}, None],

			['cmd.run', ["./configure.sh", ],                                                     {'env' : "DEBIAN_FRONTEND=noninteractive", "cwd" : '/scraper', 'runas' : 'scrapeworker'}, ['Setup OK! System is configured for launch']],
		]

		failures = 0
		err = None

		for command, args, kwargs, expect in commands:
			while True:
				self.log.info("Executing command '%s', args: '%s', kwargs: '%s'", command, args, kwargs)
				resp = self.local.cmd(clientname,
					fun=command,
					arg=args,
					kwarg=kwargs
					)


				self.log.info("Command executed. Clientname in response: %s", clientname in resp)
				try:
					if clientname in resp:
						if expect:
							self.validate_expect(resp[clientname], expect)
						elif resp is False:
							raise marshaller_exceptions.InvalidDeployResponse("Command returned a failure result: '%s' (%s, %s)" % (command, args, kwargs))
						failures = 0
						break
				except (marshaller_exceptions.InvalidDeployResponse, marshaller_exceptions.InvalidExpectParameter) as e:
					failures += 1
					err = e
				except Exception as e:
					failures += 1
					err = e
				tries = 3
				self.log.error("Command failed (attempt %s of %s)!", failures, tries)
				self.log.error("Response:")
				self.log.error("%s", resp)
				if failures > tries:
					if err is not None:
						raise err
					else:
						raise marshaller_exceptions.VmCreateFailed("Failed to create VM!")

			if resp[clientname]:
				if isinstance(resp[clientname], dict):
					text = pprint.pformat(resp[clientname])
					for line in text.split("\n"):
						self.log.info("	%s", line)
				elif isinstance(resp[clientname], str):
					for line in resp[clientname].split("\n"):
						self.log.info("	%s", line)
				else:
					self.log.warning("Unknown type: %s", type(resp[clientname]))
					text = pprint.pformat(resp[clientname])
					for line in text.split("\n"):
						self.log.warning("	%s", line)
			else:
				self.log.info("Received empty response")


		if resp[clientname] and not resp[clientname].strip().endswith('Setup OK! System is configured for launch'):
			raise VmInitError("Setup command did not return success!")

		self.log.info("Node configured! Starting scraper client!")
		jobid = self.local.cmd_async(tgt=clientname, fun='cmd.run', arg=["screen -d -m ./run.sh", ], kwarg={"cwd" : '/scraper', 'runas' : 'scrapeworker'})
		self.log.info("Job id: '%s'", jobid)

	################################################################################################

	def make_client(self, clientname, provider, kwargs):

		self.log.info("Creating instance...")
		self.log.info("	Client name: '%s'", clientname)
		self.log.info("	using provider: '%s'", provider)
		self.log.info("	kwargs: '%s'", kwargs)
		try:
			ret = self.cc.create(names=[clientname], provider=provider, **kwargs)

			self.log.info("Response: %s", ret)
			if clientname in ret and not ret[clientname]:
				raise marshaller_exceptions.VmCreateFailed("Failed when creating VM? Exception: %s" % e)

			self.log.info("Instance created!")

			if provider == 'linode' and clientname in ret and ret[clientname] is False:
				raise marshaller_exceptions.VmCreateFailed("Failed when creating Linode VM?")

		except Exception as e:
			traceback.format_exc()

			# DO Doesn't list the lcoation where they temporarily disabled VM creation, so if that specific thing
			# happens, raise a more specific error.
			if " The specified location, " in str(e) and ", could not be found." in str(e) and provider == 'digitalocean':
				raise marshaller_exceptions.LocationNotAvailableResponse("Location error when creating VM. Exception: %s" % e)

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

			nodes = [nodename for _host, nodename in self.list_nodes()]
			loops += 1

	################################################################################################

	def list_nodes(self):

		sources = [
			'digitalocean',
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
		images = self.cc.list_images(provider='digitalocean')
		sizes = self.cc.list_sizes(provider='digitalocean')
		pprint.pprint(images)
		pprint.pprint(sizes)


# So.... vultur support is currently fucked.
# Waiting on https://github.com/saltstack/salt/issues/37040

def vtest():
	herder = VpsHerder(debug=True)

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
	herder = VpsHerder(debug=True)

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
	herder = VpsHerder(debug=True)

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
	herder = VpsHerder(debug=True)

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
	herder = VpsHerder(debug=True)

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

def destroy_test_minions():
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
	herder.generate_do_conf()
	# herder.list_do_options()


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

		"destroy-test-minions"     : destroy_test_minions,
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
