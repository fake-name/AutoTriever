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

		self.plugins = loadPlugins()

		self.classCache = {}

	def doCall(self, module, call, call_args, call_kwargs):
		if not module in self.classCache:
			self.classCache[module] =  self.plugins[module]()

		self.log.info("Calling module '%s'", module)
		self.log.info("internal call name '%s'", call)
		self.log.info("Args '%s'", call_args)
		self.log.info("Kwargs '%s'", call_kwargs)

		return self.classCache[module].calls[call](*call_args, **call_kwargs)

	def process(self, command):
		if not 'module' in command:
			self.log.error("No 'module' in message!")

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

		ret = self.doCall(command['module'], command['call'], args, kwargs)

		response = {
			'ret' : ret,
			'success' : True,
			'cancontinue' : True
		}


		return response


def getPythonScriptModules():
	scriptDir = os.path.split(os.path.realpath(__file__))[0]
	moduleDir = os.path.join(scriptDir, "modules")

	ret = []
	for fName in os.listdir(moduleDir):

		# Skip files without a '.py' extension
		if not fName.endswith(".py"):
			continue
		fPath = os.path.join(moduleDir, fName)
		fName = fName.split(".")[0]

		# Skip the __init__.py file.
		if fName == "__init__":
			continue

		ret.append((fPath, fName))

	return ret

def findPluginClass(module):

	interfaces = []
	for item in dir(module):
		if not item.startswith("PluginInterface_"):
			continue

		plugClass = getattr(module, item)
		if not "name" in dir(plugClass):
			continue

		interfaces.append((plugClass.name, plugClass))

	return interfaces
def loadPlugins():
	modules = getPythonScriptModules()
	ret = {}

	for fPath, modName in modules:
		loader = SourceFileLoader(modName, fPath)
		mod = loader.load_module()
		plugClasses = findPluginClass(mod)
		for key, pClass in plugClasses:
			if key in ret:
				raise ValueError("Two plugins providing an interface with the same name? Name: '%s'" % key)

			ret[key] = pClass
	return ret


def test():
	import deps.logSetup
	import logging
	log = logging.getLogger("Main.Importer")
	deps.logSetup.initLogging()
	log.info("Testing import options")

	plugins = loadPlugins()
	for name, plugin in plugins.items():
		print(name)
		p = plugin()
		print(p.calls)



if __name__ == "__main__":
	test()
