
import urllib.parse
import logging
import bs4
import WebRequest

from autotriever.modules.SmartFetch import ProcessorBase
from . import Processor_CrN
from . import Processor_Lndb
from . import Processor_Qidian
from . import Processor_StoriesOnline


class SmartDispatcher(ProcessorBase.ProcessorBase):

	log = logging.getLogger("Main.SmartDispatcher")

	def __init__(self, wg:WebRequest.WebGetRobust):
		super().__init__()
		self.wg = wg


	def smartGetItem(self, itemUrl, *args, **kwargs):
		netloc = urllib.parse.urlsplit(itemUrl).netloc

		if netloc.lower().endswith("creativenovels.com"):
			crproc   = Processor_CrN.CrNFixer(self.wg)
			return crproc.smartGetItem(itemUrl=itemUrl, *args, **kwargs)
		elif netloc.lower().endswith("lndb.info"):
			lnproc   = Processor_Lndb.LndbProcessor(self.wg)
			return lnproc.forwad_render_fetch(itemUrl=itemUrl, *args, **kwargs)
		elif netloc.lower().endswith("webnovel.com"):
			qiproc   = Processor_Qidian.QidianProcessor(self.wg)
			return qiproc.forwad_render_fetch(itemUrl=itemUrl, *args, **kwargs)
		elif netloc.lower().endswith("webnovel.com"):
			soproc   = Processor_StoriesOnline.StoriesOnlineFetch(self.wg)
			return soproc.getpage(requestedUrl=itemUrl, *args, **kwargs)
		else:
			return self.wg.getItem(itemUrl=itemUrl, *args, **kwargs)

