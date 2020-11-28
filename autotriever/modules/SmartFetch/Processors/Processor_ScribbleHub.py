
import urllib.parse
import re
import ast
import bs4
import WebRequest

from . import ProcessorBase


def stripUrlQuery(url):
	'''
	Trim any trailing query from a URL.

	Will raise an exception on a non-valid URLs
	'''
	url_split = urllib.parse.urlsplit(url)
	url_root = urllib.parse.urlunparse(url_split[:3] +("", "", ""))
	return url_root

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

		if len(url_segs) >= 5:
			if url_segs[3] == 'series' and sid:
				self.log.info("Chapter list page. Inserting ToC")
				contentstr = self._render_sh_toc(url, sid, contentstr)

			if url_segs[3] == 'genre' or url_segs[3] == 'tag':
				self.log.info("Tag or genre listing page. Inserting pagination links")
				contentstr = self._render_sh_pagination(url, contentstr)


		return contentstr
		# contentstr = self._cleanup_content(contentstr)

	def _extract_scripts(self, soup):

		trigger_strings = [
				'#pagination-profile-recent',
				'#pagination-mesh-toc',
			]
		for item in soup.find_all("script"):
			stxt =  item.get_text()
			if any([tmp in stxt for tmp in trigger_strings]):
				tmp_str = "{\n"
				for row in stxt.split("\n"):
					if   "itemsOnPage" in row:
						tmp_str += row.replace("itemsOnPage", '"itemsOnPage"') + "\n"
					elif "items" in row:
						tmp_str += row.replace("items", '"items"') + "\n"
					elif "prevText" in row:
						tmp_str += row.replace("prevText", '"prevText"') + "\n"
					elif "hrefTextPrefix" in row:
						tmp_str += row.replace("hrefTextPrefix", '"hrefTextPrefix"') + "\n"
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
				return ast.literal_eval(tmp_str)

		return None



	def _render_sh_pagination(self, url, content):


		soup = WebRequest.as_soup(content)

		meta = self._extract_scripts(soup)

		# print("Meta:", meta)
		# print("bool(toc_goes_here): ", bool(toc_goes_here))
		# print('items' in meta, 'displayedPages' in meta)

		fic_div = soup.find("div", class_='wrap')

		pagination_div = soup.new_tag('span')

		required = [
			'items',
			'currentPage',
			'hrefTextPrefix',

		]

		url_base = stripUrlQuery(url)

		#import IPython
		#IPython.embed()

		if fic_div and all([tmp in meta for tmp in required]):
			for pg_num in range(1, meta['items']):
				if pg_num != int(meta['currentPage']):
					pg_link = soup.new_tag('a')
					pg_link.attrs['href'] = "{}{}{}".format(url_base, meta['hrefTextPrefix'], pg_num)
					pg_link.string        = "Pg '{}'".format(pg_num)
					pagination_div.append(soup.new_tag('br'))
					pagination_div.append(pg_link)
				else:
					pg_link = soup.new_tag('span')
					pg_link.string = "Pg '{}'".format(pg_num)
					pagination_div.append(soup.new_tag('br'))
					pagination_div.append(pg_link)

		fic_div.append(pagination_div)



		ret = soup.prettify()
		rx = re.compile("<a.+?&.+?>")

		for match in rx.findall(ret):
			old = match
			new = match.replace("&amp;", "&")
			ret = ret.replace(old, new)


		return ret



	def _render_sh_toc(self, url, sid, content):
		'''
			action: wi_getreleases_pagination
			pagenum: 1
			mypostid: 100965
		'''

		soup = WebRequest.as_soup(content)
		toc_goes_here = soup.find("div", class_='wi_fic_table')

		meta = self._extract_scripts(soup)

		# print("Meta:", meta)
		# print("bool(toc_goes_here): ", bool(toc_goes_here))
		# print('items' in meta, 'displayedPages' in meta)

		meta_series_name = soup.find("meta", property="og:title")
		if meta_series_name:
			meta_series_name = meta_series_name.get("content", None)

		fs = soup.find("div", class_='fic_stats')


		if fs and meta_series_name:
			wln_link = soup.new_tag('a')
			wln_link.attrs['href'] = 'https://www.wlnupdates.com/search?{}'.format(urllib.parse.urlencode({'title': meta_series_name}))
			wln_link.string        = "WLN Link for series '{}'".format(meta_series_name)
			fs.insert(0, soup.new_tag('br'))
			fs.insert(0, wln_link)

			for tag in fs.find_all("span", class_='st_item'):
				tag.insert_after(soup.new_tag('br'))

		if toc_goes_here and meta and 'items' in meta and 'displayedPages' in meta:
			toc_list = toc_goes_here.find("ol")
			if not toc_list:
				self.log.warning("No ToC List?")


			try:
				pages = int(meta['items'])
			except ValueError:
				self.log.warning("Could not convert available page number to integer (%s)!", meta['items'])

				return soup.prettify()

			self.log.info("Displayed Pages")
			chapters = ""
			for x in range(pages):
				post_params = {
					"action"   : "wi_getreleases_pagination",
					"pagenum"  : x+1,
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

			self.log.info("Found %s chapters to insert into ToC", len(chapters))
		else:
			self.log.warning("No ToC found to insert?")



		return soup.prettify()





