



import urllib.parse
import bs4
from . import ProcessorBase


class GravityTalesProcessor(ProcessorBase.ProcessorBase):

	log_name = "Main.Processor.GravityTales"

	@staticmethod
	def wants_url(lowerspliturl, mimetype):
		if 'text/html' not in mimetype:
			return False

		return lowerspliturl.netloc.endswith("gravitytales.com")


	def preprocess_content(self, url, lowerspliturl, mimetype, contentstr):
		if not isinstance(contentstr, str):
			return contentstr

		if '<div id="bot-alert" class="alert alert-info">' in contentstr:
			self.log.info("Bot bullshit. Stepping through.")
			contentstr = self.botGarbage(contentstr, url)
			self.log.info("Retreived clickwrapped content successfully")
		return contentstr

	def botGarbage(self, content, url):
		errs = 0
		while '<div id="bot-alert" class="alert alert-info">' in content:
			if errs > 1:
				return content

			self.log.info("Trying phantomjs fetch to circumvent recaptcha")
			self.wg.resetUa()
			content, dummy_name, dummy_mime = self.wg.chromiumGetRenderedItem(url)
			errs += 1

		return content
