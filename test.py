
# This has to go first because of monkeypatching in local_entry_point
from autotriever import local_entry_point # noqa

import sys
import logging
import json
import threading

from selenium import webdriver
import selenium.webdriver.chrome.service
import selenium.webdriver.chrome.options
import WebRequest

import autotriever.deps.logSetup
import autotriever.plugin_loader
from autotriever import dispatcher

def get_plugin_lut():
	log = logging.getLogger("Main.Importer")
	log.info("Testing import options")

	plugins = autotriever.plugin_loader.loadPlugins('modules', "PluginInterface_")

	return plugins

def test_storiesonline():
	try:
		settings = local_entry_point.loadSettings()
	except local_entry_point.SettingsLoadFailed:
		print("WARNING! No settings!")
		print("Cannot test storiesonline!")
		return

	instance = dispatcher.RpcCallDispatcher(settings)
	for x in range(12880, 12980):
		url = "http://storiesonline.net/s/{num}/".format(num=x)

		args = (url, )
		kwargs = {}
		try:
			ret = instance.doCall("StoriesOnlineFetch", "getpage", call_args=args, call_kwargs=kwargs, context_responder=None)
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



def debug_print(debug_f, plg_f):

	print("Known plugin commands:")
	for command in plg_f.keys():
		print("	", command)
	print("Known debug commands:")
	for command in debug_f.keys():
		print("	", command)



def test_smart_dispatcher():
	try:
		settings = local_entry_point.loadSettings()
	except local_entry_point.SettingsLoadFailed:
		print("WARNING! No settings!")
		print("Cannot test storiesonline!")
		return

	test_urls = [
		'http://www.google.com',
		'http://lndb.info/',
		'http://lndb.info/light_novel/Dousei_Kara_Hajimaru_Otaku_Kanojo_no_Tsukurikata',
		'http://lndb.info/light_novel/Trinity_Blood:_Reborn_on_the_Mars',
		'http://lndb.info/light_novel/Trinity_Blood:_Reborn_on_the_Mars/vol/11962',
		'https://storiesonline.net',
		'https://www.asianhobbyist.com',
		'https://www.asianhobbyist.com/mcm-370/',
		'https://www.asianhobbyist.com/oma-165/',
		'https://creativenovels.com/',
		'https://creativenovels.com/novel/my-entire-class-was-summoned-to-another-world-except-for-me/',
		'https://creativenovels.com/novel/womanizing-mage/',
		'http://gravitytales.com/',
		'http://gravitytales.com/novel/immortal-and-martial-dual-cultivation',
		'http://gravitytales.com/novel/immortal-and-martial-dual-cultivation/imdc-chapter-3',
		'https://tags.literotica.com/',
		'http://www.livejournal.com/',
		'https://www.reddit.com/r/starrankhunter/',
		'https://www.tgstorytime.com/',
		'https://www.flying-lines.com/chapter/the-evil-prince-and-his-precious-wife:the-sly-lady/c-127',
		"https://www.flying-lines.com/novel/the-evil-prince-and-his-precious-wife:the-sly-lady",
	]

	lock_dict = local_entry_point.initialize_manager()

	instance = dispatcher.RpcCallDispatcher(settings, lock_dict=lock_dict)
	for test_url in test_urls:


		args = (test_url, )
		kwargs = {}

		_ = instance.doCall("SmartWebRequest", "smartGetItem", call_args=args, call_kwargs=kwargs, context_responder=None)
		print("Called OK!")
		# print(ret)



CALL_LUT = {
	"test-stories-online" : test_storiesonline,
	"test-custom-chrome"  : test_custom_chrome,
	"test-dispatcher"     : dispatcher.test,
	"preproc-test"        : test_smart_dispatcher,
}

def test():


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
	autotriever.deps.logSetup.initLogging()
	# logging.basicConfig(level=logging.INFO)
	# test_custom_chrome()
	test()
	# test_smart_dispatcher()
