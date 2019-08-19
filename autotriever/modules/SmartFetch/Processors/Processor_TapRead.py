
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


PAGE_URL = "http://www.tapread.com/book/index/{book_id}/{chapter_id}"
TOC_URL  = "http://www.tapread.com/book/detail/{book_id}"


class TapReadProcessor(ProcessorBase.ProcessorBase):

	log_name = "Main.Processor.TapRead"

	@staticmethod
	def wants_url(lowerspliturl, mimetype):
		if 'text/html' not in mimetype:
			return False

		return lowerspliturl.netloc.endswith("tapread.com")



	def preprocess_content(self, url, lowerspliturl, mimetype, contentstr):
		soup = WebRequest.as_soup(contentstr)

		module = soup.body.attrs.get("page_module", None)

		self.log.info("Page module: %s", module)

		if module == "readBox":
			self.log.info("Chapter page. Inserting nav links")
			soup = self.insert_chapter_nav_links(soup)

		if module == "bookDetail":
			self.log.info("Chapter page. Inserting nav links")
			soup = self.insert_toc_nav_links(soup)

		soup = self._cleanup_content(soup)

		return soup.prettify()


	###################################################################################################
	# CrN garbage
	###################################################################################################


	def _cleanup_content(self, soup):


		bad_classes = [
			'signin-tip',
			't-header-rig',
			'person-box',
			'recommend-wrapper',
			'comment-wrapper',
			'bot-handle',
			'fix-nav',
			'empty-container',
		]

		for bad_class in bad_classes:
			for bogus in soup.find_all("div", class_=bad_class):
				bogus.decompose()

		return soup

	def insert_toc_nav_links(self, soup):


		book_id = soup.body.attrs.get("bookid", None)

		if not book_id:
			self.log.warning("No book ID (%s)", book_id)
			return soup

		post_params = {
			"bookId"    : book_id,
		}

		extra_headers = {
			"X-Requested-With" : "XMLHttpRequest",
		}


		cdat = self.wg.getJson("http://www.tapread.com/book/contents", postData=post_params, addlHeaders=extra_headers)


		toc_goes_here = soup.find("div", class_='recommend')
		if not (cdat.get('msg') == 'success' and toc_goes_here):
			self.log.error("Missing section -> %s, %s!", cdat.get('msg'), toc_goes_here)
			return soup


		toc_result = cdat['result']

		contents_table = soup.new_tag("table")

		for seg in toc_result['chapterList']:
			if seg['priceUnit'] != 0:
				continue

			row = soup.new_tag("tr")

			td = soup.new_tag("td")
			row.append(td)
			newlink = soup.new_tag("a", href=PAGE_URL.format(book_id=book_id, chapter_id=seg['chapterId']))
			newlink.string = seg['chapterName']
			td.append(newlink)

			td = soup.new_tag("td")
			row.append(td)
			td.string = seg['pubTime']

			contents_table.append(row)

		toc_goes_here.replace_with(contents_table)



		return soup


	def insert_chapter_nav_links(self, soup):

		book_id = soup.body.attrs.get("bookid", None)
		cur_id  = soup.body.attrs.get("chapterid", None)


		post_params = {
			"bookId"    : book_id,
			"chapterId" : cur_id
		}
		extra_headers = {
			"X-Requested-With" : "XMLHttpRequest",
		}

		if not (book_id and cur_id):
			self.log.warning("No book ID and chapter ID (%s, %s)", book_id, cur_id)
			return soup

		cdat = self.wg.getJson("http://www.tapread.com/book/chapter", postData=post_params, addlHeaders=extra_headers)


		fill_div = soup.find("div", class_="section-list")
		nav_div  = soup.find("div", class_="section-end")

		if not (cdat.get('msg') == 'success' and fill_div and nav_div):
			self.log.error("Missing section -> %s, %s, %s!", cdat.get('msg'), fill_div, nav_div)
			return soup

		chapter_result = cdat['result']

		content = WebRequest.as_soup(chapter_result['content'])

		content.html.unwrap()
		content.body.unwrap()

		chap_div = soup.new_tag("div")
		chap_tit = soup.new_tag("h3")
		chap_tit.string = chapter_result['chapterName']
		chap_div.append(chap_tit)
		chap_div.append(content)


		fill_div.replace_with(chap_div)


		chp_div           = soup.new_tag("div")

		prev_id = chapter_result['preChapterId']
		next_id = chapter_result['nextChapterId']

		if prev_id:
			prev_chp_tag = soup.new_tag("a")
			prev_chp_tag['href']   = PAGE_URL.format(book_id=book_id, chapter_id=prev_id)
			prev_chp_tag.string    = "Previous Chapter"
			chp_div.append(prev_chp_tag)


		toc_chp_tag = soup.new_tag("a")
		toc_chp_tag['href']   = TOC_URL.format(book_id=book_id)
		toc_chp_tag.string    = "TOC"
		chp_div.append(toc_chp_tag)

		if next_id:
			next_chp_tag = soup.new_tag("a")
			next_chp_tag['href']   = PAGE_URL.format(book_id=book_id, chapter_id=next_id)
			next_chp_tag.string    = "Next Chapter"
			chp_div.append(next_chp_tag)


		nav_div.replace_with(chp_div)


		return soup





