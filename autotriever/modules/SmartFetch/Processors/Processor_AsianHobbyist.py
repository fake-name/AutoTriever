

import WebRequest

from . import ProcessorBase

class AsianHobbyistProcessor(ProcessorBase.ProcessorBase):

	log_name = "Main.Processor.AsianHobbyist"

	@staticmethod
	def wants_url(lowerspliturl, mimetype):
		if 'text/html' not in mimetype:
			return False

		return lowerspliturl.netloc.endswith("asianhobbyist.com")


	def preprocess_content(self, url, lowerspliturl, mimetype, contentstr):
		if mimetype != 'text/html':
			return contentstr

		soup = WebRequest.as_soup(contentstr)

		for bogus in soup.find_all("a", href='https://www.asianhobbyist.com/android-mobile-app-live/'):
			bogus.decompose()

		# There should be some content. If the page is completely empty of text, it was probably an error.
		# assert len(soup.get_text(strip=True)) > 50

		return soup.prettify()

