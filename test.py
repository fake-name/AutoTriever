

import dispatcher
import sys
import deps.logSetup
import logging





def get_plugin_lut():
	log = logging.getLogger("Main.Importer")
	deps.logSetup.initLogging()
	log.info("Testing import options")

	initCalls = dispatcher.loadPlugins('init', 'InitSystem_')

	for initCall in initCalls:
		p = initCalls[initCall]()
		print(p.calls['init']())
		print('InitCall: ', initCall)

	plugins = dispatcher.loadPlugins('modules', "PluginInterface_")

	return plugins

def test_storiesonline():
	import main
	settings = main.loadSettings()
	dispatch_cls = dispatcher.RpcCallDispatcher(settings)
	for x in range(12880, 12980):
		url = "http://storiesonline.net/s/{num}/".format(num=x)

		args = (url, )
		kwargs = {}
		try:
			ret = dispatch_cls.doCall("StoriesOnlineFetch", "getpage", call_args=args, call_kwargs=kwargs)
			print(ret)
		except Exception:
			pass

CALL_LUT = {
	"stories-online" : test_storiesonline,

}

def test():

	deps.logSetup.initLogging()
	if len(sys.argv) < 2:
		plugin_lut = get_plugin_lut()
		print("ERROR:")
		print("You must specify a plugin to test!")
		print("Known commands:")
		for command in CALL_LUT.keys():
			print("	", command)
		return

	target = sys.argv[1]

	if target in CALL_LUT:
		CALL_LUT[target]()

	else:
		print("Unknown arg!")
		print("Known commands:")
		for command in CALL_LUT.keys():
			print("	", command)



if __name__ == "__main__":
	test()
