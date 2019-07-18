

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


def print_help():
	log.info("AutoTreiver CLI")
	plugins = plugin_loader.loadPlugins('modules', "PluginInterface_")
	if len(sys.argv) == 1:
		log.info("No arguments! You need to specify at least a plugin and function name.")
	if len(sys.argv) == 2:
		log.info("Insufficent arguments! You need to specify at least a plugin and function name.")
	else:
		log.info("Error!.")
	log.info("Further function parameters will be deduced from the relevant function type annotations.")
	log.info("Usage: python3 cli.py <module> <function-name> [args]")
	log.info("Plugins:")

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


def cast_param(arg_str, want_type):

	if want_type.annotation != inspect.Parameter.empty:

		return want_type.annotation(arg_str)
	else:
		return arg_str



def try_call(func, args):
	'''
	Try to call function `func` with passed array of arguments `args`.
	Validates that arguments args are of the correct length.
	'''


	sig = inspect.signature(func)

	log.info("Function signature:")
	log.info("	%s", str(sig))


	cast_args = [cast_param(in_arg, param_type) for in_arg, param_type in zip(args, sig.parameters.values())]
	req_params = [parm for parm in sig.parameters if (
		    sig.parameters[parm].default == inspect.Parameter.empty
		and sig.parameters[parm].kind    != inspect.Parameter.VAR_POSITIONAL
		and sig.parameters[parm].kind    != inspect.Parameter.VAR_KEYWORD
		)]

	if len(sig.parameters) == 0 and len(cast_args) == 0:
		log.info("No params required: %s", func)
		ret = func()
		log.info("Called!")
		return ret

	elif len(sig.parameters) == len(cast_args):
		log.info("Matching param count: %s", func)
		ret = func(*cast_args)
		log.info("Called!")
		return ret

	elif len(cast_args) >= len(req_params) and len(cast_args) <= len(sig.parameters):
		log.info("Partial coverage of arguments, including all required: %s", cast_args)
		ret = func(*cast_args)
		log.info("Called!")
		return ret
	else:
		log.error("Could not invoke function!")
		log.error("Available arguments: %s", cast_args)
		log.error("Function arguments: %s", [(parm, sig.parameters[parm].default, sig.parameters[parm].kind) for parm in sig.parameters])

def dispatch(args):
	assert len(args) >= 3
	mod_name, func_name, params = args[1], args[2], args[3:]
	plugins = plugin_loader.loadPlugins('modules', "PluginInterface_")

	if mod_name not in plugins:
		log.error("Plugin module '%s' not found!", mod_name)
		print_help()
		return

	instance = plugins[mod_name]()


	if '__setup__' in instance.calls:
		# and then call it's setup method
		try:
			instance.calls['__setup__']()
		except Exception:
			log.error("Plugin failed to initialize: '%s'!", plugins[mod_name])
			for line in traceback.format_exc().split("\n"):
				log.error("	%s", line.rstrip())

			raise

	if func_name not in instance.calls:
		log.error("Plugin module '%s' does not have call named '%s' not found!" % (mod_name, func_name))
		print_help()
		return


	ret = try_call(instance.calls[func_name], params)

	print("Returned")
	print("-#-#-#-#-#-#-#-#-#-#-#-#-#-#-#-#-#-#-#-#-#-#-#-#-#-#-#-#-#-#-#-#-#-#-#-#-#-#-#-#-#-#")
	print()
	print(ret)


def go():
	autotriever.deps.logSetup.initLogging(logLevel=logging.INFO)
	if len(sys.argv) < 3:
		print_help()
	else:
		dispatch(sys.argv)


if __name__ == "__main__":
	go()
