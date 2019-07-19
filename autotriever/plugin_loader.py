#!/usr/bin/env python3
from importlib.machinery import SourceFileLoader
import os.path
import os
import pprint


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

		# We need the full module path for import, so we can use relative
		# imports in the module itself.
		relp = os.path.relpath(fPath, os.getcwd())
		fName = relp.split(".")[0]
		fName = fName.replace("/", ".")


		ret.append((fPath, fName))

	return ret

def findPluginClass(module, prefix):
	# print("Finding plugin classes for: ", module, prefix)
	interfaces = []
	# print("interfaces: ", interfaces)
	for item in dir(module):
		# print("	item: ", item)
		if not item.startswith(prefix):
			continue

		plugClass = getattr(module, item)
		if not "name" in dir(plugClass):
			continue

		interfaces.append((plugClass.name, plugClass))
	return interfaces

def dedup_modules(modules):
	# orig = len(modules)
	#
	modules = [item for item in modules if 'modules/__init__.py' not in item[0]]
	modules = list(set(modules))

	# after = len(modules)
	# assert orig == after

	return modules

def loadPlugins(onPath, prefix):
	# print("Loading modules on path: ", onPath)
	modules = getPythonScriptModules(onPath)
	modules = dedup_modules(modules)
	# pprint.pprint("Modules:")
	# pprint.pprint(modules)
	ret = {}

	for fPath, modName in modules:
		loader = SourceFileLoader(modName, fPath)
		mod = loader.load_module()
		# print('modName:', modName)
		plugClasses = findPluginClass(mod, prefix)
		# print("PlugClasses: ", plugClasses)
		for key, pClass in plugClasses:
			if key in ret:
				# Something somewhere seems to be caching loaded module components, so
				# we only complain if the class is actually different
				if ret[key] != pClass:
					print("WARNING? - Two plugins providing an interface with the same name? Name: '%s'" % key)
					print("Classes: %s, %s" % (ret[key], pClass))

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
