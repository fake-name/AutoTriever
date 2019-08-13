


import urllib.parse
import re
import bs4
import WebRequest

from . import ProcessorBase


shortened_netlocs = [
	'wp.me',
	'feedproxy.google.com',
]

search_regex = re.compile(
	"|".join(
			[
				r"https?://(?:www\.)?{}".format(nl.replace(r".", r"\."))
			for
				nl
			in
				shortened_netlocs]
		)
	, re.IGNORECASE)



# All tags you need to look into to do link canonization
# source: http://stackoverflow.com/q/2725156/414272
# "These aren't necessarily simple URLs ..."
urlContainingTargets = [
	('a',          'href'),
	('applet',     'codebase'),
	('area',       'href'),
	('base',       'href'),
	('blockquote', 'cite'),
	('body',       'background'),
	('del',        'cite'),
	('form',       'action'),
	('frame',      'longdesc'),
	('frame',      'src'),
	('head',       'profile'),
	('iframe',     'longdesc'),
	('iframe',     'src'),
	('input',      'src'),
	('input',      'usemap'),
	('ins',        'cite'),
	('link',       'href'),
	('object',     'classid'),
	('object',     'codebase'),
	('object',     'data'),
	('object',     'usemap'),
	('q',          'cite'),
	('script',     'src'),
	('audio',      'src'),
	('button',     'formaction'),
	('command',    'icon'),
	('embed',      'src'),
	('html',       'manifest'),
	('input',      'formaction'),
	('source',     'src'),
	('video',      'poster'),
	('video',      'src'),
	('img',        'longdesc'),
	('img',        'src'),
	('img',        'usemap'),
]

head_cache = {}

class LinkUnshortenerProcessor(ProcessorBase.ProcessorBase):

	log_name = "Main.Processor.LinkUnshortener"


	@staticmethod
	def wants_url(lowerspliturl, mimetype):
		if 'text/html' not in mimetype:
			return False

		return True

	def fix_shortened(self, page_html):
		soup = WebRequest.as_soup(page_html)



		# All links have been resolved to fully-qualified paths at this point.
		ret = []
		# print("Extracting links!")
		for tag, attr in urlContainingTargets:

			for link in soup.findAll(tag):

				# Skip empty anchor tags
				try:
					url = link[attr]

					if search_regex.search(url):
						if url in head_cache:
							link[attr] = head_cache[url]
						else:
							resolved = self.wg.getHead(url)
							link[attr]      = resolved
							head_cache[url] = resolved
				except KeyError:
					continue


		return soup.prettify()

	def preprocess_content(self, url, lowerspliturl, mimetype, contentstr):
		if isinstance(contentstr, bytes):
			contentstr = bs4.UnicodeDammit(contentstr).unicode_markup



		if search_regex.search(contentstr):
			contentstr = self.fix_shortened(contentstr)

		return contentstr
