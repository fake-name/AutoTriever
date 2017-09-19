

import dispatcher
import sys
import deps.logSetup
import logging
import time
import util.WebRequest

from selenium import webdriver
import selenium.webdriver.chrome.service
import selenium.webdriver.chrome.options


# def get_plugin_lut():
# 	log = logging.getLogger("Main.Importer")
# 	log.info("Testing import options")

# 	plugins = dispatcher.loadPlugins('modules', "PluginInterface_")

# 	return plugins

# def test_storiesonline():
# 	import main
# 	try:
# 		settings = main.loadSettings()
# 	except main.SettingsLoadFailed:
# 		print("WARNING! No settings!")
# 		print("Cannot test storiesonline!")
# 		return

# 	dispatch_cls = dispatcher.RpcCallDispatcher(settings)
# 	for x in range(12880, 12980):
# 		url = "http://storiesonline.net/s/{num}/".format(num=x)

# 		args = (url, )
# 		kwargs = {}
# 		try:
# 			ret = dispatch_cls.doCall("StoriesOnlineFetch", "getpage", call_args=args, call_kwargs=kwargs)
# 			print(ret)
# 		except Exception:
# 			pass



def test_custom_chrome():

	wg = util.WebRequest.WebGetRobust()
	print(wg)

	wg.getItemChromium("http://www.google.com")
	wg.getHeadTitleChromium("http://www.google.com")
	wg.getHeadChromium("http://www.google.com")

	print("Cookies:")
	print(wg.cj)




# CALL_LUT = {
# 	"test-stories-online" : test_storiesonline,
# 	"test-custom-chrome" : test_custom_chrome,
# 	"test-dispatcher" : dispatcher.test,
# }

# def debug_print(debug_f, plg_f):

# 	print("Known plugin commands:")
# 	for command in plg_f.keys():
# 		print("	", command)
# 	print("Known debug commands:")
# 	for command in debug_f.keys():
# 		print("	", command)

# def test():

# 	deps.logSetup.initLogging()

# 	plugin_lut = get_plugin_lut()

# 	if len(sys.argv) < 2:
# 		print("ERROR:")
# 		print("You must specify a plugin to test!")
# 		debug_print(CALL_LUT, plugin_lut)
# 		return

# 	target = sys.argv[1]

# 	if target in plugin_lut:
# 		instance = plugin_lut[target]()
# 		instance.test()
# 		print(instance)

# 	elif target in CALL_LUT:
# 		CALL_LUT[target]()

# 	else:
# 		print("Unknown arg!")
# 		debug_print(CALL_LUT, plugin_lut)




if __name__ == "__main__":
	logging.basicConfig(level=logging.DEBUG)
	test_custom_chrome()
	# test()
