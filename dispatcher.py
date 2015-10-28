#!/usr/bin/env python3
import client
from importlib.machinery import SourceFileLoader
import os.path
import os

class RpcCallDispatcher(client.RpcHandler):
	'''
	dispatch calls.

	Call dispatch is done dynamically, by looking up methods in dynamically loaded plugins.

	'''


	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)

		self.log.info("Loading plugins from disk.")
		self.plugins = loadPlugins('modules', "PluginInterface_")
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
					p.calls['init']()
				except Exception:
					self.log.error("Plugin failed to initialize: '%s'. Disabling!")
					self.plugins.pop(plugin_name)

		self.log.info("Active post-init plugins: %s", len(self.plugins))
		for item in self.plugins.keys():
			self.log.info("Enabled plugin: '%s'", item)
		self.classCache = {}




	def doCall(self, module, call, call_args, call_kwargs):
		if not module in self.classCache:
			self.log.info("First call to module '%s'", module)
			self.classCache[module] =  self.plugins[module]()
			self.log.info("Module provided calls: '%s'", self.classCache[module].calls.keys())

		self.log.info("Calling module '%s'", module)
		self.log.info("internal call name '%s'", call)
		# self.log.info("Args '%s'", call_args)
		# self.log.info("Kwargs '%s'", call_kwargs)

		return self.classCache[module].calls[call](*call_args, **call_kwargs)

	def process(self, command):
		if not 'module' in command:
			self.log.error("No 'module' in message!")
			self.log.error("Message: '%s'", command)

			ret = {
				'success'     : False,
				'error'       : "No module in message!",
				'cancontinue' : True
			}

			if 'extradat' in command:
				ret['extradat'] = command['extradat']

			return ret

		if not 'call' in command:
			self.log.error("No 'call' in message!")

			ret = {
				'success'     : False,
				'error'       : "No call in message!",
				'cancontinue' : True
			}
			if 'extradat' in command:
				ret['extradat'] = command['extradat']
			return ret



		args = []
		kwargs = {}
		if 'args' in command:
			args = command['args']
		if 'kwargs' in command:
			kwargs = command['kwargs']

		ret = self.doCall(command['module'], command['call'], args, kwargs)
		# print(ret)
		response = {
			'ret'          : ret,
			'success'      : True,
			'cancontinue'  : True,
			'dispatch_key' : command['dispatch_key'],
			'module'       : command['module'],
			'call'         : command['call'],
		}

		if 'extradat' in command:
			response['extradat'] = command['extradat']

		return response


def getPythonScriptModules(dirPath):
	scriptDir = os.path.split(os.path.realpath(__file__))[0]
	moduleDir = os.path.join(scriptDir, dirPath)

	ret = []
	for fName in os.listdir(moduleDir):


		fPath = os.path.join(moduleDir, fName)

		if fPath.endswith("__pycache__"):
			continue

		if os.path.isdir(fPath):
			ret += getPythonScriptModules(fPath)

		# Skip files without a '.py' extension
		if not fName.endswith(".py"):
			continue


		fName = fName.split(".")[0]


		ret.append((fPath, fName))

	return ret

def findPluginClass(module, prefix):
	# print("Finding plugin classes for: ", module, prefix)
	interfaces = []
	# print("interfaces: ", interfaces)
	for item in dir(module):
		if not item.startswith(prefix):
			continue

		plugClass = getattr(module, item)
		if not "name" in dir(plugClass):
			continue

		interfaces.append((plugClass.name, plugClass))
	return interfaces

def dedup_modules(modules):
	orig = len(modules)
	modules = [item for item in modules if 'modules/__init__.py' not in item[0]]
	modules = list(set(modules))
	after = len(modules)
	return modules

def loadPlugins(onPath, prefix):
	# print("Loading modules on path: ", onPath)
	modules = getPythonScriptModules(onPath)
	modules = dedup_modules(modules)
	ret = {}

	for fPath, modName in modules:
		loader = SourceFileLoader(modName, fPath)
		mod = loader.load_module()
		# print("Loader:", loader, "module: ", mod)
		plugClasses = findPluginClass(mod, prefix)
		for key, pClass in plugClasses:
			if key in ret:
				print("WARNING? - Two plugins providing an interface with the same name? Name: '%s'" % key)

			ret[key] = pClass
	return ret


def test():
	import deps.logSetup
	import logging
	log = logging.getLogger("Main.Importer")
	deps.logSetup.initLogging()
	log.info("Testing import options")

	initCalls = loadPlugins('init', 'InitSystem_')

	for initCall in initCalls:
		p = initCalls[initCall]()
		print(p.calls['init']())
		print('InitCall: ', initCall)

	plugins = loadPlugins('modules', "PluginInterface_")

	print("plugins:", plugins)

	for plugin in plugins:
		print("Plugin: ", plugin)

if __name__ == "__main__":
	test()
