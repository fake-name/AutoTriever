
import re
import time
import bs4
import urllib.parse
import WebRequest

from autotriever.util.Mailinator import MailinatorClient
from . import PreemptProcessorBase

class FoxTellerFetch(PreemptProcessorBase.PreemptProcessorBase):

	log_name = "Main.Processor.FoxTeller"

	@staticmethod
	def preemptive_wants_url(lowerspliturl:tuple):
		return lowerspliturl.netloc.endswith("foxteller.com")

	def de_garbage_html(self, html):
		soup = WebRequest.as_soup(html)

		# Seriously, bite me.
		garbage_inline = re.compile(r'Please contact us at contact@foxteller\.com if you see this on another site')

		for bad in soup.find_all("span", text=garbage_inline):
			bad.decompose()


		return soup.prettify()



	def premptive_handle_content(self, url):
		'''
		Get content with bullshit JS rendering.
		'''

		wrapper_step_through_timeout = 60
		loading_str                  = "Chapter loading..."


		with self.wg._chrome_context(url, extra_tid=False) as cr:
			self.wg._syncIntoChromium(cr)
			try:

				response = cr.blocking_navigate_and_get_source(url)

				raw_url = cr.get_current_url()
				fileN = urllib.parse.unquote(urllib.parse.urlparse(raw_url)[2].split("/")[-1])
				fileN = bs4.UnicodeDammit(fileN).unicode_markup

				# Short circuit for the binary content case.
				if response['binary']:
					return response['content'], fileN, "application/x-binary"

				self.log.info("Waiting for content to render...")

				for _ in range(wrapper_step_through_timeout):
					body = cr.get_rendered_page_source()
					if loading_str not in body:
						self.log.info("Content appears to have rendered!")
						return self.de_garbage_html(body), fileN, "text/html"
					time.sleep(1)

			finally:
				self.wg._syncOutOfChromium(cr)

		raise WebRequest.GarbageSiteWrapper("Could not render JS content!")


