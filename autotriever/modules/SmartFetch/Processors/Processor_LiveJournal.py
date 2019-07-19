

import urllib.parse
import bs4


from . import ProcessorBase


class LJProcessor(ProcessorBase.ProcessorBase):

	log_name = "Main.Processor.Livejournal"

	@staticmethod
	def wants_url(lowerspliturl, mimetype):
		if 'text/html' not in mimetype:
			return False

		return lowerspliturl.netloc.endswith("livejournal.com")


	def preprocess_content(self, url, lowerspliturl, mimetype, contentstr):
		if not isinstance(contentstr, str):
			return contentstr

		if '<form method="POST" action="http://www.livejournal.com/misc/adult_explicit.bml">' in contentstr:
			self.log.info("Adult clickwrap page. Stepping through")
			contentstr = self._acceptAdult(contentstr, url)
			self.log.info("Retreived clickwrapped content successfully")
		return contentstr


	def _acceptAdult(self, content, _):
		soup = bs4.BeautifulSoup(content, "lxml")
		formdiv = soup.find('div', class_='b-msgsystem-warningbox-confirm')

		target = formdiv.form['action']
		bounce = formdiv.input
		button = formdiv.button

		form_args = {
			button['name'] : button['value'],
			bounce['name'] : bounce['value'],
		}

		new = self.wg.getpage(target, postData=form_args)
		assert '<form method="POST" action="http://www.livejournal.com/misc/adult_explicit.bml">' not in new
		return new
