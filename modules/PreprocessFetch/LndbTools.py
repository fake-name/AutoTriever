
import logging
from util.WebRequest import WebGetRobust
from util.WebRequest import Exceptions as WgExceptions

from modules.PreprocessFetch import ProcessorBase

class LndbProcessor(ProcessorBase.ProcessorBase):

	log = logging.getLogger("Main.LndbFeedProcessor")

	def __init__(self):
		super().__init__()
		self.wg = WebGetRobust()


	def forwad_render_fetch(self, *args, **kwargs):
		content, fileN, mType = self.wg.getItem(*args, **kwargs)

		if 'text/html' in mType:
			content = self._check_lndb_release(content)

		return content, fileN, mType


	def _check_lndb_release(self, contentstr):

		return contentstr

		# content = self.wg.getpage(feed_url)


