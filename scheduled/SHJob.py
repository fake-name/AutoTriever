
import scheduled.model as model

import os.path
import site
import datetime
import logging
import random
import time
import traceback
import urllib.error
import WebRequest


wd = os.path.abspath(os.getcwd())
relp = "./scheduled/NuUpdate"
module_path = os.path.join(wd, relp)
abs_module_path = os.path.abspath(module_path)
site.addsitedir(abs_module_path)

from WebMirror.OutputFilters.util.TitleParsers import title_from_html

def rebaseUrl(url, base):
	"""Rebase one url according to base"""

	parsed = urllib.parse.urlparse(url)
	if parsed.scheme == '' or parsed.netloc == '':
		return urllib.parse.urljoin(base, url)
	else:
		return url

REFETCH_INTERVAL = datetime.timedelta(days=5)
FETCH_ATTEMPTS   = 3
SINGLETON_WG     = WebRequest.WebGetRobust(use_global_tab_pool=False)

HOMEPAGE_URL = "https://www.scribblehub.com/rssfeed.php?type=main"

class SHMonitor():
	def __init__(self):

		self.log = logging.getLogger("Main.SHMonitor")


		self.wg = SINGLETON_WG



	def extract_feed_urls(self, seriesPageUrl, soup):
		'''
		This is a mess, and relies on some slightly broken parsing of the feed
		xml content by lxml in HTML mode.

		It works, but is probably brittle. I should really do the parsing locally via beautifulstonesoup.
		'''
		ret = []
		for link in soup.find_all("link"):
			url = str(link.next).strip()
			if 'www.scribblehub.com/read/' in link.next:
				ret.append(url)

		return ret

	def __check_load_page(self, url, sess):

		content = None

		item = sess.query(model.WebPages).filter(model.WebPages.url == url).scalar()
		was_new = False
		if item:
			if item.fetchtime > datetime.datetime.now() - REFETCH_INTERVAL:
				self.log.info("URL '%s' fetched within refetch interval (%s). Not fetching", url, REFETCH_INTERVAL)
				return
			else:
				self.log.info("Refetching URL '%s'", url)

		else:
			was_new = True
			self.log.info("URL '%s' is new!", url)
			item = model.WebPages(
					url          = url,
					addtime      = datetime.datetime.now(),
				)

		try:
			content, _name, mime, url = self.wg.getFileNameMimeUrl(url, addlHeaders={'Referer': HOMEPAGE_URL})
			item.state        = "complete"
			item.errno        = None
			item.mimetype     = mime
			item.is_text      = "text" in mime
			item.content      = content
			item.fetchtime    = datetime.datetime.now()

		except WebRequest.WebGetException:
			for line in traceback.format_exc().split("\n"):
				self.log.error(line)
			item.state        = "error"
			item.errno        = -1
			item.fetchtime    = datetime.datetime.now()

		except urllib.error.URLError:
			for line in traceback.format_exc().split("\n"):
				self.log.error(line)
			item.state        = "error"
			item.errno        = -1
			item.fetchtime    = datetime.datetime.now()


		if was_new:
			sess.add(item)

		sess.commit()


		pg_title = title_from_html(content)
		self.log.info("Fetched '%s' with title '%s'", url, pg_title)
		sleep = random.triangular(3,10,30)
		self.log.info("Sleeping %s", sleep)
		time.sleep(sleep)

		return content

	def __get_series_url(self, page_html):
		soup = WebRequest.as_soup(page_html)

		index_link = soup.find(class_='c_index')

		if not index_link:
			self.log.warning("No index link on page!")
			return None

		if not index_link.a:
			self.log.warning("No anchor tag in index button on page!")
			return None

		# Returns None on missing atribute
		return index_link.a.get("href")

	def fetch_update_series_pages(self, urls):
		with model.session_context() as sess:
			for url in urls:
				item_page = self.__check_load_page(url, sess)

				if item_page:
					series_url = self.__get_series_url(item_page)
					self.log.info("Series page: %s", series_url)

					# I can't see how this would ever fail, but who knows
					if series_url:
						self.__check_load_page(series_url, sess)
	def go(self):

		with model.session_context() as sess:
			pass

		soup = self.wg.getSoup(HOMEPAGE_URL)



		series_pages = self.extract_feed_urls(HOMEPAGE_URL, soup)
		self.fetch_update_series_pages(series_pages)



if __name__ == "__main__":
	logging.basicConfig(level=logging.DEBUG)

	mon = SHMonitor()

	mon.go()





