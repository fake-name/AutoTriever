

import queue
import time
import threading
import inspect
import traceback
import sys
import json
import logging
import os.path
import os

import autotriever.deps.logSetup

from autotriever import plugin_loader

log = logging.getLogger("Main.CLI")

def try_call(func, args):
	'''
	Try to call function `func` with passed array of arguments `args`.
	Validates that arguments args are of the correct length.
	'''


	sig = inspect.signature(func)

	if len(sig.parameters) == 0 and len(args) == 0:
		print("No params required: ", func)
		func()
		print("Called!")
		return True

	if len(sig.parameters) == len(args):
		print("Matching param count: ", func)
		func(*args)
		return True

	req_params = [parm for parm in sig.parameters if sig.parameters[parm].default == inspect.Parameter.empty]
	if len(args) >= len(req_params) and len(args) <= len(sig.parameters):
		print("Partial coverage of arguments, including all required: ", args)
		func(*args)
		return True

	return False

def dispatch(args):
	pass

def print_help():
	print("AutoTreiver CLI")
	plugins = plugin_loader.loadPlugins('modules', "PluginInterface_")
	print("No arguments! You need to specify at least a plugin and function name.")
	print("Further function parameters will be deduced from the relevant function type annotations.")
	print("Plugins:")

	for plugin_name in list(plugins.keys()):

		# Instantiate the initialization class
		p = plugins[plugin_name]()
		log.info("Plugin '%s' provides the following %s calls:", plugin_name, len(p.calls))
		for call_name, call_func in p.calls.items():
			log.info("	Call: '%s' -> %s", call_name, inspect.signature(call_func))


		if '__setup__' in p.calls:
			# and then call it's setup method
			try:
				p.calls['__setup__']()
			except Exception:
				log.error("Plugin failed to initialize: '%s'. Disabling!", plugin_name)
				for line in traceback.format_exc().split("\n"):
					log.error("	%s", line.rstrip())
				plugins.pop(plugin_name)


	log.info("Active post-init plugins: %s", len(plugins))
	for item in plugins.keys():
		log.info("Enabled plugin: '%s'", item)




def go():
	autotriever.deps.logSetup.initLogging(logLevel=logging.INFO)
	if len(sys.argv) == 1:
		print_help()
	else:
		dispatch(sys.argv)


if __name__ == "__main__":
	go()
