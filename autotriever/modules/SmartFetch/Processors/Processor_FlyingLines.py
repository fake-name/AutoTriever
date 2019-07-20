
import logging
import pprint
import re
import ast
import json
import feedparser
import traceback
from feedgen.feed import FeedGenerator
import WebRequest

from . import ProcessorBase

class FlyingLinesProcessor(ProcessorBase.ProcessorBase):

	log_name = "Main.Processor.FlyingLines"

	@staticmethod
	def wants_url(lowerspliturl, mimetype):
		if 'text/html' not in mimetype:
			return False

		return lowerspliturl.netloc.endswith("flying-lines.com")

	def preprocess_content(self, url, lowerspliturl, mimetype, contentstr):
		if not isinstance(contentstr, str):
			return contentstr

		if '<span class="chapter_title">chapter title for js | </span>' in contentstr:
			self.log.info("Idiotic jerberscript render. Fetching...")
			contentstr = self._fetch_jerberscript_chapter(contentstr)
			self.log.info("Successfully did JS forward rendering.")

		if '<span>Table of Contents</span>' in contentstr:
			self.log.info("Fixing ToC ordering")
			contentstr = self._reorder_toc(contentstr)
			self.log.info("Table of contents reordered")

		return contentstr


	def _general_clean(self, soup):

		for bad in soup.find_all("div", class_='modal-login'):
			bad.decompose()
		for bad in soup.find_all("div", class_='side_bar'):
			bad.decompose()
		for bad in soup.find_all("div", class_='f-modal-content'):
			bad.decompose()
		for bad in soup.find_all("li", class_='subscribe'):
			bad.decompose()
		for bad in soup.find_all("span", class_='process'):
			bad.decompose()
		for bad in soup.find_all("a", href='javascript:;'):
			bad.decompose()

		return soup

	def _reorder_toc(self, contentstr):
		soup = WebRequest.as_soup(contentstr)
		soup = self._general_clean(soup)

		content_area = soup.find("ul", class_='details-content')

		comment_div = soup.find("div", class_='comment')
		if not comment_div:
			return soup.prettify()

		comment_div.extract()

		new_li = soup.new_tag("li")
		new_li.append(comment_div)

		content_area.append(new_li)

		return soup.prettify()

	def _fetch_jerberscript_chapter(self, contentstr):
		soup = WebRequest.as_soup(contentstr)

		soup = self._general_clean(soup)

		conttag = soup.find("div", class_='main_body')

		cid = conttag.attrs.get('data-chapter-id')
		ctitle = soup.find("span", class_="chapter_title")


		if not cid:
			if ctitle:
				ctitle.string = "No chapter ID found!"
			return soup.prettify()

		# This is dynamic in the page jerberscript. I'm being lazy here.
		chap_endpoint = "https://www.flying-lines.com/chapter/{cid}".format(cid=cid)

		chap_ep = self.wg.getJson(chap_endpoint)

		if not ('status' in chap_ep and chap_ep['status'] == 'success'):
			if ctitle:
				ctitle.string = "Chapter json fetch failed!"
			return soup.prettify()

		cdat = chap_ep['data']

		ctitle.string = cdat['chapter_title']

		cbody = WebRequest.as_soup(cdat['chapter_content'])

		# Goddammit
		cbody.html.unwrap()
		cbody.body.unwrap()

		conttag.append(cbody)


		for bad in soup.find_all("p", class_='siteCopyrightInfo'):
			bad.decompose()

		itemp = cdat['path']

		_, ctype, series, chap = itemp.split("/")

		ignored__prefix, chap_num = chap.split("-")[:2]

		chap_num = int(chap_num)

		chap_format = "https://www.flying-lines.com/{ctype}/{series}/c-{chap}"

		next_chap = chap_format.format(ctype=ctype, series=series, chap=chap_num + 1)
		prev_chap = chap_format.format(ctype=ctype, series=series, chap=chap_num - 1)

		toc_chap  = "https://www.flying-lines.com/novel/{series}/".format(series=series)

		chp_div           = soup.new_tag("div")

		next_chp_tag = soup.new_tag("a")
		next_chp_tag['href']   = next_chap
		next_chp_tag.string    = "Next Chapter"

		toc_chp_tag = soup.new_tag("a")
		toc_chp_tag['href']   = toc_chap
		toc_chp_tag.string    = "TOC"

		prev_chp_tag = soup.new_tag("a")
		prev_chp_tag['href']   = prev_chap
		prev_chp_tag.string    = "Previous Chapter"

		chp_div.append(prev_chp_tag)
		chp_div.append(toc_chp_tag)
		chp_div.append(next_chp_tag)

		conttag.append(chp_div)

		return soup.prettify()

