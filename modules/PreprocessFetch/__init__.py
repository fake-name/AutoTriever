
import abc
import logging
import re
import time
import datetime
import json
import feedparser
from feedgen.feed import FeedGenerator
from util.WebRequest import WebGetRobust
from util.WebRequest import Exceptions as WgExceptions

class ProcessorBase(object, metaclass=abc.ABCMeta):

	@abc.abstractproperty
	def log(self):
		pass

	@abc.abstractmethod
	def __init__(self):
		pass

	@abc.abstractmethod
	def get_results(self):
		pass

class QidianProcessor(ProcessorBase):

	log = logging.getLogger("Main.QidianFeedProcessor")

	def __init__(self, feed_url, have_info):
		self.wg = WebGetRobust()
		self.feed_url  = feed_url
		self.have_info = have_info


	def _check_qidian_release(self, entry):

		# Fake various components if the rss source is fucked up.
		if not 'guid' in entry:
			entry['guid'] = entry['link'] + entry['title']
		if not "authors" in entry:
			entry['authors'] = ""


		if entry['guid'] in self.have_info:
			have = self.have_info[entry['guid']]
		else:
			have = {}

		if not 'resolved_url' in have:
			if '/rssbook/' in entry['link']:
				content = self.wg.getpage(entry['link'])

				url_re = re.compile(r"g_data\.url ?= ?\'(.+?)';")
				url = url_re.search(content)

				if not url:
					print("No actual content URL found")
					print(content)
					return None


				url = url.group(1)
				if url.startswith("//"):
					url = 'https:' + url

				print("resolved item url out to %s" % url)

				have['resolved_url'] = url
			else:
				have['resolved_url'] = entry['link']

		else:
			print("Already have resolved URL: %s" % have['resolved_url'])

		entry['link'] = have['resolved_url']

		if not 'ad_free' in have:
			soup = self.wg.getSoup(entry['link'])

			for bad_script in soup.find_all("script"):
				bad_script.decompose()

			print("Checking for ad")
			if 'Watch ad to get chapter' in soup.prettify():
				print("Item still ad-wrapped. Not adding.")
				return None
			else:
				print("Item has no ad.")
				have['ad_free'] = True


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
			# authors
			# title_detail
			# published
			# extra-info
			# title
			#

		content = feed.rss_str(pretty=True)

		return content


	def get_results(self):


		# print("Feed url:", self.feed_url)
		# print("Meta:", self.have_info)

		content = self.wg.getpage(self.feed_url)
		parsed = feedparser.parse(content)

		filtered = []
		bad = 0
		for entry in parsed['entries']:
			try:
				ok = self._check_qidian_release(entry)
				if ok:
					filtered.append(ok)
				else:
					bad += 1
			except WgExceptions.FetchFailureError:
				bad += 1

			self.log.info("Have %s OK releases, %s bad ones.", len(filtered), bad)

		parsed['entries'] = filtered


		return self.reserialize_feed(parsed)

class PluginInterface_PreprocessFetch(object):

	name = 'PreprocessFetch'

	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)


		self.calls = {
			'qidianSmartFeedFetch'                  : self.qidianSmartFeedFetch,
		}


	def qidianSmartFeedFetch(self, feed_url, meta):

		proc = QidianProcessor(feed_url, meta)
		content = proc.get_results()

		return content, '', 'application/rss+xml'

	def test(self):
		print("Exec()ing `runTest.sh` from directory root!")

		import subprocess
		command = "./runTests.sh"

		process = subprocess.Popen(command.split(), stdout=subprocess.PIPE)
		output, error = process.communicate()

		print("Command output: ", output)
		print("Command errors: ", error)
