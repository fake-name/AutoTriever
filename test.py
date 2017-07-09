

import dispatcher
import sys
import deps.logSetup
import logging
import logging
import time
import util.WebRequest

from selenium import webdriver
import selenium.webdriver.chrome.service
import selenium.webdriver.chrome.options


def get_plugin_lut():
	log = logging.getLogger("Main.Importer")
	log.info("Testing import options")

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



def test_custom_chrome():

	wg = util.WebRequest.WebGetRobust()
	print(wg)

	wg._initCrWebDriver()


	# print("Navigating")
	# driver.get('https://www.wlnupdates.com/')

	# print("Configuring viewport.")
	# # driver.set_window_size(1920, 1080)

	driver = wg.cr_driver


	print("Getting URL")
	driver.get('http://10.1.1.8:33507/')

	print("Sleeping")
	time.sleep(2) # Let the user actually see something!

	# search_entry = driver.find_element_by_id("srch-term")
	# print(search_entry)

	# search_btn = driver.find_element_by_name("title")
	# search_btn.click()

	# print("Sleeping")
	# time.sleep(2) # Let the user actually see something!


	# print("Html:")
	# print(driver.execute_script("return document.getElementsByTagName('html')[0].innerHTML"))

	print("Cookies:")
	print(driver.get_cookies())

	print("User agent: ")
	print(driver.execute_script("return navigator.userAgent"))

	del wg


CALL_LUT = {
	"test-stories-online" : test_storiesonline,
	"test-custom-chrome" : test_custom_chrome,
	"test-dispatcher" : dispatcher.test,
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
		CALL_LUT[target]()

	else:
		print("Unknown arg!")
		debug_print(CALL_LUT, plugin_lut)



if __name__ == "__main__":
	# test_custom_chrome()
	test()
