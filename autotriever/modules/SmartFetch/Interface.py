
import logging
import urllib.parse

import bs4
import WebRequest

from autotriever.modules.SmartFetch.Processors import Processor_ShortenedLinks
from autotriever.modules.SmartFetch.Processors import Processor_CrN
from autotriever.modules.SmartFetch.Processors import Processor_Qidian
from autotriever.modules.SmartFetch.Processors import Processor_Literotica
from autotriever.modules.SmartFetch.Processors import PreemptProcessor_Lndb
from autotriever.modules.SmartFetch.Processors import PreemptProcessor_StoriesOnline
from autotriever.modules.SmartFetch.Processors import Processor_Reddit
from autotriever.modules.SmartFetch.Processors import Processor_TgStoryTime
from autotriever.modules.SmartFetch.Processors import Processor_LiveJournal
from autotriever.modules.SmartFetch.Processors import Processor_ShortSites
from autotriever.modules.SmartFetch.Processors import Processor_AsianHobbyist
from autotriever.modules.SmartFetch.Processors import Processor_GravityTales
from autotriever.modules.SmartFetch.Processors import Processor_FlyingLines
from autotriever.modules.SmartFetch.Processors import PreemptProcessor_FoxTeller

#pylint: disable=R1705

PREEMPTIVE_PROCESSORS = [
	PreemptProcessor_Lndb.LndbProcessor,
	PreemptProcessor_StoriesOnline.StoriesOnlineFetch,
	PreemptProcessor_FoxTeller.FoxTellerFetch,
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

	# This processor has to go last.
	Processor_ShortenedLinks.LinkUnshortenerProcessor,
]

class PluginInterface_SmartFetch(object):

	name = 'SmartWebRequest'

	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		self.log = logging.getLogger("Main.SmartFetcher")

		self.wg = WebRequest.WebGetRobust()

		self.calls = {
			'qidianSmartFeedFetch'                  : self.qidianSmartFeedFetch,
			'qidianProcessReleaseList'              : self.qidianProcessReleaseList,
			'smartGetItem'                          : self.smartGetItem,

			'getpage'                               : self.wg.getpage,
			'getItem'                               : self.wg.getItem,
			'getHead'                               : self.wg.getHead,
			'getFileAndName'                        : self.wg.getFileAndName,
			'addCookie'                             : self.wg.addCookie,
			'addSeleniumCookie'                     : self.wg.addSeleniumCookie,
			'stepThroughCloudFlare'                 : self.wg.stepThroughCloudFlare,

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
				processed = True
				content = processor.preprocess(url=itemUrl, lowerspliturl=lowerspliturl, mimeType=mType, content=content, wg=self.wg)

		if processed:
			self.log.info("All preprocessors completed!")
		return content, fileN, mType




	# def smartGetItem(self, itemUrl:str, *args, **kwargs):
	# 	netloc = urllib.parse.urlsplit(itemUrl).netloc

	# 	if netloc.lower().endswith("creativenovels.com"):
	# 		crproc   = Processor_CrN.CrNFixer(self.wg)
	# 		return crproc.smartGetItem(itemUrl=itemUrl, *args, **kwargs)
	# 	elif netloc.lower().endswith("lndb.info"):
	# 		lnproc   = Processor_Lndb.LndbProcessor(self.wg)
	# 		return lnproc.forward_render_fetch(itemUrl=itemUrl, *args, **kwargs)
	# 	elif netloc.lower().endswith("webnovel.com"):
	# 		qiproc   = Processor_Qidian.QidianProcessor(self.wg)
	# 		return qiproc.forwad_render_fetch(itemUrl=itemUrl, *args, **kwargs)
	# 	elif netloc.lower().endswith("webnovel.com"):
	# 		soproc   = Processor_StoriesOnline.StoriesOnlineFetch(self.wg)
	# 		return soproc.getpage(requestedUrl=itemUrl, *args, **kwargs)
	# 	else:
	# 		return self.wg.getItem(itemUrl=itemUrl, *args, **kwargs)
