
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

		print("Check: ", lowerspliturl.netloc.endswith("flying-lines.com"))
		return lowerspliturl.netloc.endswith("flying-lines.com")

	def preprocess_content(self, url, lowerspliturl, mimetype, contentstr):
		if not isinstance(contentstr, str):
			return contentstr

		print()
		if '<!-- 阅读内容区域 -->' in contentstr:
			self.log.info("Idiotic jerberscript render. Fetching...")
			contentstr = self._fetch_jerberscript_chapter(contentstr)
			self.log.info("Successfully did JS forward rendering.")

		if '<span>Table of Contents</span>' in contentstr:
			self.log.info("Fixing ToC ordering")
			contentstr = self._fix_reorder_toc(url, contentstr)
			self.log.info("Table of contents reordered")

		return contentstr


	def _general_clean(self, soup):

		gargage_divs = [
			'user-alert',
			'browser-push',
			'alert-box-click',
			'modal-login',
			'footer',
			'side_bar',
			'f-modal-content',
		]

		for garbage_div in gargage_divs:
			for bad in soup.find_all("div", class_=garbage_div):
				bad.decompose()
		for bad in soup.find_all("li", class_='subscribe'):
			bad.decompose()
		for bad in soup.find_all("span", class_='process'):
			bad.decompose()
		for bad in soup.find_all("footer", class_='footer'):
			bad.decompose()
		for bad in soup.find_all("a", href='javascript:;'):
			bad.decompose()

		return soup

	def _fix_reorder_toc(self, url, contentstr):
		soup = WebRequest.as_soup(contentstr)
		soup = self._general_clean(soup)


		url_base = url.replace("/novel/", "/chapter/").rstrip("/")


		for link_tag in soup.find_all("a", class_='menuChapterUrl'):
			link_tag['href'] = url_base + "/c-" + str(link_tag['data-chapter-number'])

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

		novel_path  = conttag.attrs.get('data-novel_path')
		chapter_num = conttag.attrs.get('data-chapternum')
		cid         = conttag.attrs.get('data-chapter-id')
		ctitle      = soup.find("span", class_="chapter_title")


		if not cid:
			self.log.error("No chapter ID found!")
			if ctitle:
				ctitle.string = "No chapter ID found!"
			return soup.prettify()

		# This is dynamic in the page jerberscript. I'm being lazy here.
		# chap_endpoint = "https://www.flying-lines.com/chapter/{cid}".format(cid=cid)
		chap_endpoint = "https://www.flying-lines.com/h5/novel/{novel_path}/{chap_num}".format(novel_path=novel_path, chap_num=chapter_num)

		chap_ep = self.wg.getJson(chap_endpoint)

		if not ('status' in chap_ep and chap_ep['status'] == 200):
			self.log.error("Chapter json fetch failed!")
			if ctitle:
				ctitle.string = "Chapter json fetch failed!"
			return soup.prettify()

		cdat = chap_ep['data']

		ctitle.string = cdat['title']

		cbody = WebRequest.as_soup(cdat['content'])

		# Goddammit
		cbody.html.unwrap()
		cbody.body.unwrap()

		conttag.append(cbody)


		for bad in soup.find_all("p", class_='siteCopyrightInfo'):
			bad.decompose()

		nav_endpoint = "https://www.flying-lines.com/chapter/{novel_path}/c-{chap_num}"

		next_chap = nav_endpoint.format(novel_path=novel_path, chap_num=cdat['nextChapterNumber'])
		prev_chap = nav_endpoint.format(novel_path=novel_path, chap_num=cdat['lastChapterNumber'])

		toc_chap  = "https://www.flying-lines.com/novel/{series}/".format(series=novel_path)

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

		if cdat['lastChapterNumber'] > -1:
			chp_div.append(prev_chp_tag)
		chp_div.append(toc_chp_tag)
		chp_div.append(next_chp_tag)

		conttag.append(chp_div)

		return soup.prettify()

