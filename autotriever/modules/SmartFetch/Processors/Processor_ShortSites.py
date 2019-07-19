

import WebRequest

from . import ProcessorBase

class JsRendererPreprocessor(ProcessorBase.ProcessorBase):

	log_name = "Main.Processor.JsRenderer"

	@staticmethod
	def wants_url(lowerspliturl, mimetype):
		if 'text/html' not in mimetype:
			return False

		if lowerspliturl.netloc.endswith("wixsite.com"):
			return True
		if lowerspliturl.netloc.endswith("catatopatch.com"):
			return True

		return False


	def preprocess_content(self, url, lowerspliturl, mimetype, contentstr):
		soup = WebRequest.as_soup(contentstr)
		text = soup.body.get_text(strip=True).strip()

		if len(text) < 100 or True:
			self.log.info("Page has little or no body. Trying to refetch and render using chromium.")
			contentstr, dummy_fileN, dummy_mType = self.wg.chromiumGetRenderedItem(url)
		else:
			self.log.info("Page has %s char body, no re-fetch & render needed.", len(text))


		return self.clean_content(contentstr)


	def clean_content(self, contentstr):

		soup = WebRequest.as_soup(contentstr)

		for bogus in soup.find_all("video"):
			bogus.decompose()
		for bogus in soup.find_all("div", class_="siteBackground"):
			bogus.decompose()


		for div in soup.find_all("main"):
			if 'style' in div.attrs:
				del div.attrs['style']
		for div in soup.find_all("header"):
			if 'style' in div.attrs:
				del div.attrs['style']
		for div in soup.find_all("div"):
			if 'style' in div.attrs:
				del div.attrs['style']

		return soup.prettify()
