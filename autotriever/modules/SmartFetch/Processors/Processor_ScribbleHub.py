
import urllib.parse
import logging
import pprint
import ast
import bs4
import WebRequest

from . import ProcessorBase

class ScribbleHubFixer(ProcessorBase.ProcessorBase):

	log_name = "Main.Processor.ScribbleHub-Fixer"


	@staticmethod
	def wants_url(lowerspliturl, mimetype):
		if 'text/html' not in mimetype:
			return False

		return lowerspliturl.netloc.endswith("scribblehub.com")

	def preprocess_content(self, url, lowerspliturl, mimetype, contentstr):
		if isinstance(contentstr, bytes):
			contentstr = bs4.UnicodeDammit(contentstr).unicode_markup



		url_segs = url.split("/")
		sid = None
		try:
			sid = int(url_segs[4])
		except ValueError:
			pass

		if len(url_segs) >= 5 and url_segs[3] == 'series' and sid:
			self.log.info("Chapter list page. Inserting ToC")
			contentstr = self._render_sh_toc(url, sid, contentstr)


		return contentstr
		# contentstr = self._cleanup_content(contentstr)


	def _render_sh_toc(self, url, sid, content):
		'''
			action: wi_getreleases_pagination
			pagenum: 1
			mypostid: 100965
		'''

		soup = WebRequest.as_soup(content)
		toc_goes_here = soup.find("div", class_='wi_fic_table')

		meta = None

		for item in soup.find_all("script"):
			stxt =  item.get_text()
			if '#pagination-mesh-toc' in stxt:
				tmp_str = "{\n"
				for row in stxt.split("\n"):
					if   "itemsOnPage" in row:
						tmp_str += row.replace("itemsOnPage", '"itemsOnPage"') + "\n"
					elif "items" in row:
						tmp_str += row.replace("items", '"items"') + "\n"
					elif "prevText" in row:
						tmp_str += row.replace("prevText", '"prevText"') + "\n"
					elif "nextText" in row:
						tmp_str += row.replace("nextText", '"nextText"') + "\n"
					elif "displayedPages" in row:
						tmp_str += row.replace("displayedPages", '"displayedPages"') + "\n"
					elif "currentPage" in row:
						tmp_str += row.replace("currentPage", '"currentPage"') + "\n"
					elif "hrefTextPrefix" in row:
						tmp_str += row.replace("hrefTextPrefix", '"hrefTextPrefix"') + "\n"
					elif "hrefTextSuffix" in row:
						tmp_str += row.replace("hrefTextSuffix", '"hrefTextSuffix"') + "\n"

				tmp_str += "}\n"

				meta = ast.literal_eval(tmp_str)

		if toc_goes_here and meta and 'items' in meta and 'displayedPages' in meta:

			toc_list = toc_goes_here.find("ol")
			if not toc_list:
				self.log.warning("No ToC List?")


			try:
				pages = int(meta['displayedPages'])
			except ValueError:
				self.log.warning("Could not convert available page number to integer (%s)!", meta['displayedPages'])

				return soup.prettify()

			chapters = ""
			for x in range(pages):
				post_params = {
					"action"   : "wi_getreleases_pagination",
					"pagenum"  : x + 1,
					"mypostid" : sid,
				}
				extra_headers = {
					"referer" : url,
				}

				cdat = self.wg.getpage("https://www.scribblehub.com/wp-admin/admin-ajax.php", postData=post_params, addlHeaders=extra_headers)

				chapters += cdat

			csoup = WebRequest.as_soup(chapters)

			chapters = csoup.find_all("li")

			try:
				chapters.sort(key=lambda x: int(x.get("order", "0")))
			except ValueError:
				self.log.warning("Could not convert chapter sort order to integer (%s)!", chapters)
				return soup.prettify()


			# print("Contents table:", contents_table)
			toc_list.clear()
			toc_list.extend(chapters)



		return soup.prettify()





