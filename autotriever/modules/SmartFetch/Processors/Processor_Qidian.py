
import logging
import re
import json
import time
import traceback
import feedparser
from feedgen.feed import FeedGenerator
import WebRequest

from . import ProcessorBase

def unescape_inline_js_object(in_str):

	# Qidian does a bunch of escaping I don't understand, that breaks shit.
	in_str = in_str.replace("\\ ", " ")
	in_str = in_str.replace("\\'", "'")
	in_str = in_str.replace("\\/", "/")
	in_str = in_str.replace("\\<", "<")
	in_str = in_str.replace("\\>", ">")
	in_str = in_str.replace("\\&", "&")

	return in_str

def trim_to_bracket(in_str):
	assert in_str[0] == "{"
	out, in_str = in_str[0], in_str[1:]

	while in_str:
		if in_str[0] == "{":
			tmp, in_str = trim_to_bracket(in_str)
			out += tmp
		elif in_str[0] == "}":
			out += in_str[0]
			in_str = in_str[1:]
			return out, in_str
		else:
			out += in_str[0]
			in_str = in_str[1:]

	print("Non-symmetric brackets?")
	print("in_str", in_str)
	print("out   ", out)

	return out

def book_chap_ids_to_url(book_id, chap_id):

	return "https://www.webnovel.com/book/{book_id}/{chp_id}".format(
					book_id = book_id,
					chp_id  = chap_id,
				)

def make_nav_tags(soup, ctnt):
	series_id = ctnt['bookInfo']['bookId']

	next_chp_id = ctnt['chapterInfo']['nextChapterId']
	next_chp_txt = ctnt['chapterInfo']['nextChapterName']

	prev_chp_id = ctnt['chapterInfo']['preChapterId']
	prev_chp_txt = ctnt['chapterInfo']['preChapterName']

	if prev_chp_id == "-1":
		prev_tag = soup.new_tag("span")
		prev_tag.string = "No Previous Chapter"
	else:
		prev_tag = soup.new_tag("a", href=book_chap_ids_to_url(series_id, prev_chp_id))
		prev_tag.string = "Previous Chapter: " + prev_chp_txt

	if next_chp_id == "-1":
		next_tag = soup.new_tag("span")
		next_tag.string = "No Next Chapter"
	else:
		next_tag = soup.new_tag("a", href=book_chap_ids_to_url(series_id, next_chp_id))
		next_tag.string = "Next Chapter: " + next_chp_txt

	container = soup.new_tag("div")
	container.append(prev_tag)
	container.append(soup.new_tag("br"))
	container.append(next_tag)

	return container

class QidianProcessor(ProcessorBase.ProcessorBase):

	log_name = "Main.Processor.Qidian"

	@staticmethod
	def wants_url(lowerspliturl, mimetype):
		if 'text/html' not in mimetype:
			return False

		return lowerspliturl.netloc.endswith("webnovel.com")


	########################################################################
	# RSS Processing
	########################################################################

	def extract_from_meta(self, meta):
		 #                 '/274367222/msite-read-video3',
		 #                 '/274367222/msite-read-video4',
		 #                 '/274367222/msite-read-video5',
		 #                 '/274367222/web-read-video',
		 #                 '/274367222/web-read-video2',
		 #                 '/274367222/web-read-video3',
		 #                 '/274367222/web-read-video4',
		 #                 '/274367222/web-read-video5']},
		 # 'bookInfo': {'actionStatus': '30',
		 #              'authorItems': [{'guid': '2426086308',
		 #                               'id': '10411317206384101',
		 #                               'name': 'Azure_god_monarch'}],
		 #              'bookId': '10411326706031905',
		 #              'bookName': 'Modern day transcender',
		 #              'patreonLink': '',
		 #              'reviewTotal': 2,
		 #              'totalChapterNum': 7,
		 #              'totalPreChapterNum': 1,
		 #              'type': 2},
		 # 'chapterInfo': {'SSPrice': 4,
		 #                 'chapterId': '28432475277543235',
		if not "bookInfo" in meta:
			return {}
		if not "authorItems" in meta["bookInfo"]:
			return {}

		auth_names = [
			tmp.get("name", None) for tmp in meta['bookInfo']["authorItems"]
		]

		# The content string is large, and we're not using it, so
		# don't waste message space withit.
		if 'content' in meta['chapterInfo']:
			self.log.info("Removing content entry")
			meta['chapterInfo'].pop('content')
			meta['chapterInfo']['content'] = None

		auth_names = [tmp for tmp in auth_names if tmp]

		ret = {
			'authors'     : auth_names,
			'source_name' : meta["bookInfo"].get("bookName", None),
			'bookInfo'    : meta['bookInfo'],
			'chapterInfo' : meta['chapterInfo'],
		}

		return ret

	def _check_qidian_release(self, entry, have_info):

		# Fake various components if the rss source is fucked up.
		entry.setdefault('guid', entry['link'] + entry['title'])
		entry.setdefault('authors', "")

		have = have_info.get(entry['guid'], {})
		have['original_url'] = entry['link']

		if 'resolved_url' not in have:
			if '/rssbook/' in entry['link']:
				content = self.wg.getpage(entry['link'])

				url_re = re.compile(r"g_data\.url ?= ?[\'\"](.+?)[\'\"]")
				url = url_re.search(content)

				if not url:
					self.log.info("No actual content URL found")
					self.log.info("Content: %s", content)
					import pdb
					pdb.set_trace()
					return None


				url = url.group(1)
				if url.startswith("//"):
					url = 'https:' + url

				self.log.info("resolved item url out to %s", url)

				have['resolved_url'] = url
			else:
				have['resolved_url'] = entry['link']

		else:
			self.log.info("Already have resolved URL: %s", have['resolved_url'])

		entry['link'] = have['resolved_url']

		if 'ad_free' not in have:
			soup = self.wg.getSoup(entry['link'])

			rawsoupstr = str(soup)

			for bad_script in soup.find_all("script"):
				bad_script.decompose()

			header_span = soup.find("span", class_='cha-hd-mn-text')
			if header_span and header_span.a:
				have['series_name'] = header_span.a.get("title", None).strip()
				self.log.info("Extracted series name: '%s'", have['series_name'])


			self.log.info("Checking for ad")
			soupstr = str(soup)

			have['ad_free']   = False
			have['paywalled'] = True

			if soup.find("div", {"class" : "cha-content", "data-report-l1" : "3"}):
				have['ad_free'] = True
				have['paywalled'] = False
			else:
				self.log.info("Item still ad-wrapped. Not adding.")
				have['ad_free'] = False
				have['paywalled'] = True

			if (
					'cha-content _loc'        in soupstr or
					'Unlock This Chapter'     in soupstr or
					'Watch ad to get chapter' in soupstr or
					'Locked Chapter'          in soupstr
				):
				self.log.info("Item still ad-wrapped. Not adding.")
				have['ad_free'] = False
				have['paywalled'] = True

			if have['ad_free']:
				self.log.info("Item has no ad.")


			title_div = soup.find("div", class_='cha-tit')
			if title_div and title_div.h3:
				have['chap_title'] = title_div.h3.get_text(strip=True)


			chap_info = re.search(r"var chapInfo = (.*?);", rawsoupstr)
			if chap_info:
				chap_info_str = chap_info.group(1)

				# Qidian does a bunch of escaping I don't understand, that breaks shit.
				chap_info_str = chap_info_str.replace("\\ ", " ")
				chap_info_str = chap_info_str.replace("\\'", "'")
				chap_info_str = chap_info_str.replace("\\/", "/")
				chap_info_str = chap_info_str.replace("\\<", "<")
				chap_info_str = chap_info_str.replace("\\>", ">")

				try:
					self.log.info("Extracting!")
					cont = json.loads(chap_info_str)
					self.log.info("Extracted meta: %s", cont)
					for k, v in self.extract_from_meta(cont).items():
						have[k] = v
				except ValueError:
					self.log.info("Bad chapInfo")
					traceback.print_exc()
					self.log.info("Json str:")
					self.log.info("---------------")
					self.log.info("%s", chap_info_str)
					self.log.info("---------------")
					have['invalid_meta'] = chap_info.group(1)

			book_type = re.search(r"g_data\.isOriginal = '(\d)';", rawsoupstr)
			if book_type:
				self.log.info("Book Type: %s", book_type.group(1))
				typeint = book_type.group(1)
				if typeint == "1":
					have['type'] = 'translated'
				elif typeint == '2':
					have['type'] = 'oel'
				else:
					have['type'] = 'unknown!'


		self.log.info("have: %s", have)
		entry['extra-info'] = have

		return entry

	def reserialize_feed(self, content):
		feed_meta = content['feed']

		feed = FeedGenerator()

		feed.title(feed_meta['title'])
		feed.link( feed_meta['links'])
		feed.author( {'name':'John Doe','email':'john@example.de'} )
		feed.subtitle(feed_meta['subtitle'])
		feed.language('en')

		for release in content['entries']:

			ent = feed.add_entry()

			ent.title(release['title'])
			ent.summary(release['summary'])
			ent.published(release['published'])
			ent.id(release['guid'])

			linkd = release['links']
			for tmp in linkd:
				tmp['rel'] = "related"

			linkd.append({
				'rel': 'alternate',
				'type': 'text/html',
				'href': release['link']
			})

			ent.link(linkd)

			ent.content(json.dumps(release['extra-info']), type='CDATA')


		content = feed.rss_str(pretty=True)

		return content

	def process_release_list(self, url_list):
		ret = []
		for item in url_list:

			tmp = self._check_qidian_release(item, {})
			if tmp:
				ret.append(tmp)
		return ret


	def qidianProcessFeedUrls(self, feed_url, have_info):

		content = self.wg.getpage(feed_url)
		parsed = feedparser.parse(content)

		filtered = []
		bad = 0
		for entry in parsed['entries']:
			try:
				ok = self._check_qidian_release(entry, have_info)
				if ok:
					filtered.append(ok)
				else:
					bad += 1
			except WebRequest.FetchFailureError:
				bad += 1

			self.log.info("Have %s OK releases, %s bad ones.", len(filtered), bad)

		parsed['entries'] = filtered

		reserialized = self.reserialize_feed(parsed)
		return reserialized


	########################################################################
	# HTML Processing
	########################################################################

	def get_csrf_tok_from_wg(self):

		cooks = [
				cook
			for
				cook
			in
				self.wg.cj
			if
				cook.domain.endswith('webnovel.com')
			]

		csrf_token_name = "_csrfToken"

		for cook in cooks:
			if cook.name == csrf_token_name:
				return (csrf_token_name, cook.value)

		raise RuntimeError("No CSRF Cookie?")

	def _build_chapter_li(self, soup, dat, meta, vol_info = None):
		chp_tag = soup.new_tag("li")
		chp_link = soup.new_tag("a")


		for key, value in dat.items():

			chp_link['data-preprocessor-{}'.format(key)] = str(value)
		chp_link['data-preprocessor-vol']     = vol_info if vol_info else ""
		chp_link['href'] = book_chap_ids_to_url(
				book_id = meta['bookId'],
				chap_id = dat['id'],
			)

		chp_link.string = dat['name']
		chp_tag.append(chp_link)


		return chp_tag

	def _built_toc(self, soup, toc_dat):

		toc_div = soup.find(class_='power-bar-wrap')
		toc_div.clear()

		header_str = soup.new_tag("h3")
		header_str.string = "Table of Contents"
		toc_div.append(header_str)

		ul_tag = soup.new_tag("ul")

		data = toc_dat['data']

		book_info = data['bookInfo']

		if 'volumeItems' in data:
			for volume in data['volumeItems']:
				for chap in volume['chapterItems']:
					chap_li = self._build_chapter_li(soup, chap, book_info, vol_info = volume['name'])
					ul_tag.append(chap_li)

		elif 'chapterItems' in data:
			for chap in data['chapterItems']:
				chap_li = self._build_chapter_li(soup, chap, book_info)
				ul_tag.append(chap_li)
		else:
			self.log.warning("No chapter or volume items?")

		toc_div.append(ul_tag)



	def _insert_toc(self, url, contentstr):
		book_info = re.search(r"g_data.book ?= ?({.*?})<", contentstr)

		if not book_info:
			return contentstr + "<br><br><br><H1>No book info on page!</H1>"

		book_info_str = book_info.group(1)
		book_info_str = unescape_inline_js_object(book_info_str)

		self.log.info("Extracting!")
		ctnt = json.loads(book_info_str)
		# self.log.info("Extracted meta: %s", ctnt)

		_, csrf_tok = self.get_csrf_tok_from_wg()

		toc_dat = self.wg.getJson("https://www.webnovel.com/apiajax/chapter/GetChapterList?_csrfToken={csrf_tok}&bookId={book_id}&_={time_ms}".format(
					csrf_tok = csrf_tok,
					book_id  = ctnt['bookInfo']['bookId'],
					time_ms  = int(time.time() * 1000),
				)
			)

		soup = WebRequest.as_soup(contentstr)

		self._built_toc(soup, toc_dat) # in-place modify soup


		for bad in soup.find_all(class_='det-tab-nav'):
			bad.decompose()

		imgs_tag = soup.find(class_='g_thumb')
		if imgs_tag:
			for img in imgs_tag.find_all("img")[1:]:
				img.decompose()

		return soup.prettify()


	def _fix_chapter(self, url, contentstr):
		_, start_json = contentstr.split("var chapInfo= {")

		start_json = "{"+start_json
		chap_info_str, _ = trim_to_bracket(start_json)

		if not chap_info_str:
			return contentstr + "<br><br><br><H1>No chapter info on page!</H1>"

		chap_info_str = unescape_inline_js_object(chap_info_str)

		self.log.info("Extracting!")
		ctnt = json.loads(chap_info_str)
		# self.log.info("Extracted meta: %s", ctnt)


		soup = WebRequest.as_soup(contentstr)


		for bad in soup.find_all(class_='det-tab-nav'):
			bad.decompose()

		for bad in soup.find_all("para-comment"):
			bad.decompose()

		content_section = soup.find("div", class_='cha-words')

		content_section.insert_before(make_nav_tags(soup, ctnt))
		content_section.insert_after(make_nav_tags(soup, ctnt))


		return soup.prettify()


	def preprocess_content(self, url, lowerspliturl, mimetype, contentstr):
		#pylint: disable=unused-argument

		if not isinstance(contentstr, str):
			return contentstr


		if 'data-for="#contents" title="Table of Contents" class="j_show_contents"' in contentstr and '<span>Table of Contents</span></a>' in contentstr:
			self.log.info("Need to insert table of contents")
			contentstr = self._insert_toc(url, contentstr)

		if 'cha-content' in contentstr:
			self.log.info("Need to insert chapter nav links")
			contentstr = self._fix_chapter(url, contentstr)

		return contentstr


def test_unwrap_url():

	import WebRequest
	wg = WebRequest.WebGetRobust()
	url = "https://www.webnovel.com/rssbook/15298622505787905/41825301877029563/रिबर्थ-टु-अ-मिलिट्री-मैरिज-:-गुड-मॉर्निंग-चीफ/क़ियाओ-नान-आपकी-बहुत-बड़ी-फैन-है-"

	proc = QidianProcessor(wg=wg)

	item = {
		'link' : url,
		'title' : "Test What?",
	}

	print(proc)
	ret = proc._check_qidian_release(item, {})
	# print(ret)

def test_unrss():
	import WebRequest
	wg = WebRequest.WebGetRobust()
	proc = QidianProcessor(wg=wg)
	ret = proc.qidianProcessFeedUrls("https://www.webnovel.com/feed/", {})

	print(ret)

def test_bracket_segment():
	print("Bracket fiddle!")
	print(trim_to_bracket("{wat{}}asdasdasdasd"))
	print(trim_to_bracket("{wat{}} }asdasdasdasd"))
	print(trim_to_bracket("{wat{{{}} }asdasdasdasd"))

if __name__ == '__main__':

	import autotriever.deps.logSetup
	autotriever.deps.logSetup.initLogging(logLevel=logging.INFO)
	# test_unwrap_url()
	# test_unrss()
	test_bracket_segment()

