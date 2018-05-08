
import logging
import re
import json
import feedparser
from feedgen.feed import FeedGenerator
import WebRequest

from modules.PreprocessFetch import ProcessorBase

class QidianProcessor(ProcessorBase.ProcessorBase):

	log = logging.getLogger("Main.QidianFeedProcessor")

	def __init__(self):
		super().__init__()
		self.wg = WebRequest.WebGetRobust()


	def _check_qidian_release(self, entry, have_info):

		# Fake various components if the rss source is fucked up.
		entry.setdefault('guid', entry['link'] + entry['title'])
		entry.setdefault('authors', "")

		have = have_info.get(entry['guid'], {})
		have['original_url'] = entry['link']

		if 'resolved_url' not in have:
			if '/rssbook/' in entry['link']:
				content = self.wg.getpage(entry['link'])

				url_re = re.compile(r"g_data\.url ?= ?\'(.+?)';")
				url = url_re.search(content)

				if not url:
					self.log.info("No actual content URL found")
					self.log.info("Content: %s", content)
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
			if 'Unlock This Chapter' in soupstr or 'Watch ad to get chapter' in soupstr:
				self.log.info("Item still ad-wrapped. Not adding.")
				return None
			else:
				self.log.info("Item has no ad.")
				have['ad_free'] = True

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
		print()
		print()
		print(reserialized)
		print()
		print()
		return reserialized
