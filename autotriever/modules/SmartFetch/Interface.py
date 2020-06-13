
import logging
import urllib.parse

import bs4
import WebRequest
import threading

from autotriever.modules.SmartFetch.Processors import Processor_ShortenedLinks
from autotriever.modules.SmartFetch.Processors import Processor_CrN
from autotriever.modules.SmartFetch.Processors import Processor_Qidian
from autotriever.modules.SmartFetch.Processors import Processor_Literotica
from autotriever.modules.SmartFetch.Processors import Processor_Reddit
from autotriever.modules.SmartFetch.Processors import Processor_TgStoryTime
from autotriever.modules.SmartFetch.Processors import Processor_LiveJournal
from autotriever.modules.SmartFetch.Processors import Processor_ShortSites
from autotriever.modules.SmartFetch.Processors import Processor_AsianHobbyist
from autotriever.modules.SmartFetch.Processors import Processor_GravityTales
from autotriever.modules.SmartFetch.Processors import Processor_FlyingLines
from autotriever.modules.SmartFetch.Processors import Processor_TapRead
from autotriever.modules.SmartFetch.Processors import Processor_ScribbleHub

from autotriever.modules.SmartFetch.Processors import PreemptProcessor_Lndb
from autotriever.modules.SmartFetch.Processors import PreemptProcessor_StoriesOnline
from autotriever.modules.SmartFetch.Processors import PreemptProcessor_ChromeRender

#pylint: disable=R1705

PREEMPTIVE_PROCESSORS = [
	PreemptProcessor_Lndb.LndbProcessor,
	PreemptProcessor_StoriesOnline.StoriesOnlineFetch,
	PreemptProcessor_ChromeRender.FoxTellerFetch,
	PreemptProcessor_ChromeRender.MeeJeeFetch,
]

PROCESSORS = [

	Processor_CrN.CrNFixer,
	Processor_Qidian.QidianProcessor,
	Processor_Literotica.LiteroticaProcessor,
	Processor_Reddit.RedditProcessor,
	Processor_TgStoryTime.TgStoryTimeProcessor,
	Processor_LiveJournal.LJProcessor,
	Processor_ShortSites.JsRendererPreprocessor,
	Processor_AsianHobbyist.AsianHobbyistProcessor,
	Processor_GravityTales.GravityTalesProcessor,
	Processor_FlyingLines.FlyingLinesProcessor,
	Processor_TapRead.TapReadProcessor,
	Processor_ScribbleHub.ScribbleHubFixer,

	# This processor has to go last.
	Processor_ShortenedLinks.LinkUnshortenerProcessor,
]


class PluginInterface_SmartFetch(object):

	name = 'SmartWebRequest'
	serialize = False

	def __init__(self, settings=None, *args, **kwargs):
		super().__init__(*args, **kwargs)

		self.settings = settings if settings else {}

		self.log = logging.getLogger("Main.%s" % self.name)
		self.log.info("SmartFetcher!")

		twocaptcha_api = self.settings.get('captcha_solvers', {}).get('2captcha', {}).get('api_key', None)
		anticaptcha_api = self.settings.get('captcha_solvers', {}).get('anti-captcha', {}).get('api_key', None)


		self.wg = WebRequest.WebGetRobust()

		self.calls = {
			'qidianSmartFeedFetch'                  : self.qidianSmartFeedFetch,
			'qidianProcessReleaseList'              : self.qidianProcessReleaseList,
			'smartGetItem'                          : self.smartGetItem,

			'getpage'                               : self.wg.getpage,
			'getItem'                               : self.wg.getItem,
			'getHead'                               : self.wg.getHead,
			'getFileNameMime'                       : self.wg.getFileNameMime,
			# 'getFileNameMimeUrl'                    : self.wg.getFileNameMimeUrl,
			'getFileAndName'                        : self.wg.getFileAndName,
			'addCookie'                             : self.wg.addCookie,

			'chromiumGetRenderedItem'               : self.wg.chromiumGetRenderedItem,
			'getHeadChromium'                       : self.wg.getHeadChromium,
			'getHeadTitleChromium'                  : self.wg.getHeadTitleChromium,
			'getItemChromium'                       : self.wg.getItemChromium,
		}


	def qidianSmartFeedFetch(self, feed_url:str, meta):

		proc = Processor_Qidian.QidianProcessor(wg=self.wg)
		content = proc.qidianProcessFeedUrls(feed_url, meta)

		return content, '', 'application/rss+xml'

	def qidianProcessReleaseList(self, feed_urls):

		proc = Processor_Qidian.QidianProcessor(wg=self.wg)
		content = proc.process_release_list(feed_urls)

		return content


	def smartGetItem(self, itemUrl:str, *args, **kwargs):

		lowerspliturl = urllib.parse.urlsplit(itemUrl.lower())
		for processor in PREEMPTIVE_PROCESSORS:
			if processor.preemptive_wants_url(lowerspliturl=lowerspliturl):
				self.log.info("Preemptive fetch handler %s wants to modify content", processor)
				return processor.premptive_handle(url=itemUrl, wg=self.wg)

		content, fileN, mType = self.wg.getItem(itemUrl=itemUrl, *args, **kwargs)

		# Decode text-type items
		if mType.startswith('text'):
			if isinstance(content, bytes):
				content = bs4.UnicodeDammit(content).unicode_markup

		processed = False
		for processor in PROCESSORS:
			if processor.wants_url(lowerspliturl=lowerspliturl, mimetype=mType):
				self.log.info("Processor %s wants to modify content", processor)
				processed = True
				content = processor.preprocess(url=itemUrl, lowerspliturl=lowerspliturl, mimeType=mType, content=content, wg=self.wg)

		if processed:
			self.log.info("All preprocessors completed!")
		return content, fileN, mType


SINGLETON_WG   = WebRequest.WebGetRobust(use_global_tab_pool=False)
SINGLETON_LOCK = threading.Lock()

class PluginInterface_PersistentSmartFetch(object):

	name = 'PersistentSmartWebRequest'
	serialize = True

	@staticmethod
	def get_lock():
		return SINGLETON_LOCK.acquire(blocking=False)

	@staticmethod
	def free_lock():
		return SINGLETON_LOCK.release()


	def __init__(self, settings=None, *args, **kwargs):
		super().__init__(*args, **kwargs)

		self.settings = settings if settings else {}

		self.log = logging.getLogger("Main.%s" % self.name)
		self.log.info("SmartFetcher!")

		twocaptcha_api = self.settings.get('captcha_solvers', {}).get('2captcha', {}).get('api_key', None)
		anticaptcha_api = self.settings.get('captcha_solvers', {}).get('anti-captcha', {}).get('api_key', None)


		self.wg = SINGLETON_WG
		self.wg.set_twocaptcha_api_key(twocaptcha_api)
		self.wg.set_anticaptcha_api_key(anticaptcha_api)

		self.calls = {
			'smartGetItem'                          : self.smartGetItem,

			'getpage'                               : self.wg.getpage,
			'getItem'                               : self.wg.getItem,
			'getHead'                               : self.wg.getHead,
			'getFileNameMime'                       : self.wg.getFileNameMime,
			# 'getFileNameMimeUrl'                    : self.wg.getFileNameMimeUrl,
			'getFileAndName'                        : self.wg.getFileAndName,
			'addCookie'                             : self.wg.addCookie,

			'chromiumGetRenderedItem'               : self.wg.chromiumGetRenderedItem,
			'getHeadChromium'                       : self.wg.getHeadChromium,
			'getHeadTitleChromium'                  : self.wg.getHeadTitleChromium,
			'getItemChromium'                       : self.wg.getItemChromium,
		}


	def smartGetItem(self, itemUrl:str, *args, **kwargs):
		lowerspliturl = urllib.parse.urlsplit(itemUrl.lower())
		for processor in PREEMPTIVE_PROCESSORS:
			if processor.preemptive_wants_url(lowerspliturl=lowerspliturl):
				self.log.info("Preemptive fetch handler %s wants to modify content", processor)
				return processor.premptive_handle(url=itemUrl, wg=self.wg)

		content, fileN, mType = self.wg.getItem(itemUrl=itemUrl, *args, **kwargs)

		# Decode text-type items
		if mType.startswith('text'):
			if isinstance(content, bytes):
				content = bs4.UnicodeDammit(content).unicode_markup

		processed = False
		for processor in PROCESSORS:
			if processor.wants_url(lowerspliturl=lowerspliturl, mimetype=mType):
				processed = True
				content = processor.preprocess(url=itemUrl, lowerspliturl=lowerspliturl, mimeType=mType, content=content, wg=self.wg)

		if processed:
			self.log.info("All preprocessors completed!")
		return content, fileN, mType


