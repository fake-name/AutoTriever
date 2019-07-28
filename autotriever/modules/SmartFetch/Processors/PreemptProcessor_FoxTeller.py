
import logging
import time
import bs4
import WebRequest

from autotriever.util.Mailinator import MailinatorClient
from . import PreemptProcessorBase

class FoxTellerFetch(PreemptProcessorBase.PreemptProcessorBase):

	log_name = "Main.Processor.FoxTeller"

	@staticmethod
	def preemptive_wants_url(lowerspliturl:tuple):
		return lowerspliturl.netloc.endswith("foxteller.com")


	def premptive_handle_content(self, url):
		return self.wg.getItem(url)

