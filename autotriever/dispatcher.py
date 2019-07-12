#!/usr/bin/env python3
import os
import traceback

from . import client
from . import plugin_loader

class RpcCallDispatcher(client.RpcHandler):
	'''
	dispatch calls.

	Call dispatch is done dynamically, by looking up methods in dynamically loaded plugins.

	'''


	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)

		self.log.info("Loading plugins from disk.")
		self.plugins = plugin_loader.loadPlugins('modules', "PluginInterface_")
		self.log.info("Total loaded plugins pre-init: %s", len(self.plugins))
		for plugin_name in list(self.plugins.keys()):

			# Instantiate the initialization class
			p = self.plugins[plugin_name]()
			self.log.info("Plugin '%s' provides the following %s calls:", plugin_name, len(p.calls))
			for call_name in p.calls.keys():
				self.log.info("	Call: '%s'", call_name)

			if '__setup__' in p.calls:
				# and then call it's setup method
				try:
					p.calls['__setup__']()
				except Exception:
					self.log.error("Plugin failed to initialize: '%s'. Disabling!", plugin_name)
					for line in traceback.format_exc().split("\n"):
						self.log.error("	%s", line.rstrip())
					self.plugins.pop(plugin_name)


		self.log.info("Active post-init plugins: %s", len(self.plugins))
		for item in self.plugins.keys():
			self.log.info("Enabled plugin: '%s'", item)
		self.classCache = {}




	def doCall(self, module, call, call_args, call_kwargs, context_responder):
		if not module in self.classCache:
			self.log.info("First call to module '%s'", module)
			self.classCache[module] =  self.plugins[module]()
			self.log.info("Module provided calls: '%s'", self.classCache[module].calls.keys())

		self.log.info("Calling module '%s'", module)
		self.log.info("internal call name '%s'", call)
		self.log.info("Args '%s'", call_args)
		self.log.info("Kwargs '%s'", call_kwargs)

		if hasattr(self.classCache[module], "can_send_partials"):
			call_kwargs['partial_resp_interface'] = context_responder

		return self.classCache[module].calls[call](*call_args, **call_kwargs)

	def process(self, command, context_responder):
		if not 'module' in command:
			self.log.error("No 'module' in message!")
			self.log.error("Message: '%s'", command)

			ret = {
				'success'     : False,
				'error'       : "No module in message!",
				'cancontinue' : True
			}
			return ret

		if not 'call' in command:
			self.log.error("No 'call' in message!")

			ret = {
				'success'     : False,
				'error'       : "No call in message!",
				'cancontinue' : True
			}
			return ret

		args = []
		kwargs = {}
		if 'args' in command:
			args = command['args']
		if 'kwargs' in command:
			kwargs = command['kwargs']

		ret = self.doCall(command['module'], command['call'], args, kwargs, context_responder)
		# print(ret)
		response = {
			'ret'          : ret,
			'success'      : True,
			'cancontinue'  : True,
			'dispatch_key' : command['dispatch_key'],
			'module'       : command['module'],
			'call'         : command['call'],
		}

		return response



def test(plug_name=None, call_name=None, *args, **kwargs):
	import deps.logSetup
	import logging
	log = logging.getLogger("Main.Importer")
	deps.logSetup.initLogging()
	log.info("Testing import options")

	dp = RpcCallDispatcher(settings=None, lock_dict=None)

	if not plug_name:
		return

	print("Invoking arguments: '%s'" % (args, ))
	print("Invoking kwargs: '%s'" % (kwargs, ))
	return dp.doCall(plug_name, call_name, call_args=args, call_kwargs=kwargs, context_responder=None)

	# plugins = loadPlugins('modules', "PluginInterface_")

	# print("plugins:", plugins)

	# for plugin in plugins:
	# 	print("Plugin: ", plugin)

if __name__ == "__main__":
	test()