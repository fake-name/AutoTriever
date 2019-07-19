
import logging
import WebRequest

from . import PreemptProcessorBase


class LndbProcessor(PreemptProcessorBase.PreemptProcessorBase):

	log_name = "Main.Processor.LndbFeedProcessor"

	@staticmethod
	def wants_url(lowerspliturl, mimetype):
		return False

	@staticmethod
	def preemptive_wants_url(lowerspliturl:tuple):
		return lowerspliturl.netloc.endswith("lndb.info")


	def premptive_handle_content(self, url):
		content, fileN, mType = self.wg.getItem(url)

		if 'text/html' in mType:
			content = self._check_lndb_release(content)

		return content, fileN, mType


	def _check_lndb_release(self, contentstr):

		return contentstr

		# content = self.wg.getpage(feed_url)


