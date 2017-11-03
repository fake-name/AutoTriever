
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

from . import QidianTools

class PluginInterface_PreprocessFetch(object):

	name = 'PreprocessFetch'

	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)


		self.calls = {
			'qidianSmartFeedFetch'                  : self.qidianSmartFeedFetch,
			'qidianProcessReleaseList'                  : self.qidianProcessReleaseList,
		}


	def qidianSmartFeedFetch(self, feed_url, meta):

		proc = QidianTools.QidianProcessor()
		content = proc.qidianProcessFeedUrls(feed_url, meta)

		return content, '', 'application/rss+xml'

	def qidianProcessReleaseList(self, feed_urls):

		proc = QidianTools.QidianProcessor()
		content = proc.process_release_list(feed_urls)

		return content, '', 'application/rss+xml'

	def test(self):
		print("Exec()ing `runTest.sh` from directory root!")

		import subprocess
		command = "./runTests.sh"

		process = subprocess.Popen(command.split(), stdout=subprocess.PIPE)
		output, error = process.communicate()

		print("Command output: ", output)
		print("Command errors: ", error)
