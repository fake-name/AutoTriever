


import urllib.parse
import bs4

from . import ProcessorBase

class RedditProcessor(ProcessorBase.ProcessorBase):

	log_name = "Main.Processor.Reddit"


	@staticmethod
	def wants_url(lowerspliturl, mimetype):
		if 'text/html' not in mimetype:
			return False

		return lowerspliturl.netloc.endswith("reddit.com")


	def preprocess_content(self, url, lowerspliturl, mimetype, contentstr):
		if isinstance(contentstr, bytes):
			contentstr = bs4.UnicodeDammit(contentstr).unicode_markup

		if '<title>reddit.com: over 18?</title>' in contentstr:
			self.log.info("Adult clickwrap page. Stepping through")
			url = urllib.parse.urlunparse(lowerspliturl + ("",))
			contentstr = self._acceptAdult(contentstr, url)
			self.log.info("Retreived clickwrapped content successfully")

		return contentstr


	def _acceptAdult(self, content, url):

		target = "https://www.reddit.com/over18?%s" % urllib.parse.urlencode({"dest" : url})

		form_args = {
			"over18" : "yes",
		}

		new = self.wg.getpage(target, postData=form_args)
		assert '<title>reddit.com: over 18?</title>' not in new
		return new


