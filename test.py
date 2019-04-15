

import sys
import logging
import json
import threading
import dispatcher
import deps.logSetup
import WebRequest
import plugin_loader

from selenium import webdriver
import selenium.webdriver.chrome.service
import selenium.webdriver.chrome.options


def get_plugin_lut():
	log = logging.getLogger("Main.Importer")
	log.info("Testing import options")

	plugins = plugin_loader.loadPlugins('modules', "PluginInterface_")

	return plugins

def test_storiesonline():
	import main
	try:
		settings = main.loadSettings()
	except main.SettingsLoadFailed:
		print("WARNING! No settings!")
		print("Cannot test storiesonline!")
		return

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

def tfunc(threadnum):
	print("Thread %s running" % threadnum)
	wg = WebRequest.WebGetRobust()
	print(wg)

	wg.getItemChromium("http://www.google.com")
	wg.getHeadTitleChromium("http://www.google.com")
	wg.getHeadChromium("http://www.google.com")

	print("Cookies:")
	print(wg.cj)

	print("Thread %s finished" % threadnum)


def test_custom_chrome():
	t1 = threading.Thread(target=tfunc, args=(1, ))
	t2 = threading.Thread(target=tfunc, args=(2, ))
	t3 = threading.Thread(target=tfunc, args=(3, ))
	t4 = threading.Thread(target=tfunc, args=(4, ))
	t5 = threading.Thread(target=tfunc, args=(5, ))
	t1.start()
	t2.start()
	t1.join()
	t3.start()
	t2.join()
	t4.start()
	t3.join()
	t5.start()
	t4.join()
	t5.join()




CALL_LUT = {
	"test-stories-online" : test_storiesonline,
	"test-custom-chrome"  : test_custom_chrome,
	"test-dispatcher"     : dispatcher.test,
}

def debug_print(debug_f, plg_f):

	print("Known plugin commands:")
	for command in plg_f.keys():
		print("	", command)
	print("Known debug commands:")
	for command in debug_f.keys():
		print("	", command)

def test():

	deps.logSetup.initLogging()

	plugin_lut = get_plugin_lut()

	if len(sys.argv) < 2:
		print("ERROR:")
		print("You must specify a plugin to test!")
		debug_print(CALL_LUT, plugin_lut)
		return

	target = sys.argv[1]

	if target in plugin_lut:
		instance = plugin_lut[target]()
		instance.test()
		print(instance)

	elif target in CALL_LUT:
		ret = None

		if len(sys.argv) >= 4:

			plug_name = sys.argv[2]
			func_name = sys.argv[3]
			ret = CALL_LUT[target](plug_name, func_name, *sys.argv[4:])
		else:
			print("You need to specify at least the plugin + function to execute to test-dispatcher")
			print("Available calls:")
			ret = CALL_LUT[target]()

		if ret:
			with open("test-out.json", "w") as fp:
				out = json.dumps(ret, indent=4)
				fp.write(out)
		else:
			print("No call response")
	else:
		print("Unknown arg!")
		debug_print(CALL_LUT, plugin_lut)




if __name__ == "__main__":
	# logging.basicConfig(level=logging.INFO)
	# test_custom_chrome()
	test()
