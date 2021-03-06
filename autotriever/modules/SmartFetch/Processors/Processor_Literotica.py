


import bs4
import re


from . import ProcessorBase




class LiteroticaProcessor(ProcessorBase.ProcessorBase):

	log_name = "Main.Processor.Literotica"

	def preprocess_content(self, url, lowerspliturl, mimetype, contentstr):
		#pylint: disable=unused-argument
		if not isinstance(contentstr, str):
			return contentstr

		if 'favorited this story!' in contentstr:
			self.log.info("Flattening favourites!")
			contentstr = self._unwrap_favourites(contentstr)
			self.log.info("Converted favourite dialog for series.")

		if "tags.literotica.com" in lowerspliturl.netloc:
			self.log.info("Cleaning up excessive div tags.")
			contentstr = self._fix_stupid_overuse_of_div_tags(contentstr)
		return contentstr

	@staticmethod
	def wants_url(lowerspliturl, mimetype):
		if 'text/html' not in mimetype:
			return False
		return lowerspliturl.netloc.endswith("literotica.com")



	def _unwrap_favourites(self, content):

		soup = bs4.BeautifulSoup(content, "lxml")
		favp = soup.find('p', class_='b-favorites-users')
		if not favp:
			return content

		if not favp.span:
			return content
		if not favp.span.get('title', None):
			return content

		favurl_fmt = "https://search.literotica.com/search.php?type=member&q={user}"

		unames = favp.span.get('title')
		unamel = unames.split(",")
		unamel = [tmp.strip() for tmp in unamel]

		for uname in unamel:

			linka           = soup.new_tag("a")
			linka['href']   = favurl_fmt.format(user=uname)
			linka.string    = uname

			favp.append(linka)


		return soup.prettify()


	def _fix_stupid_overuse_of_div_tags(self, content):

		soup = bs4.BeautifulSoup(content, "lxml")

		bad_div_containers = soup.find_all("div", class_=re.compile("(StoryCardComponent__story__footer___|StoryCardComponent__story__content___)"))
		for bad_div_container in bad_div_containers:
			for bad_div in bad_div_container.find_all("div"):
				bad_div.name = 'span'

		rating_i = soup.find_all("i", class_=re.compile("StoryCardComponent__story__content___"))
		reads_i = soup.find_all("i", class_=re.compile("StatsStory__diagram___"))
		favourites_i = soup.find_all("i", class_=re.compile("StatsStory__heart___"))
		comments_i = soup.find_all("i", class_=re.compile("StatsStory__comment___"))
		lists_i = soup.find_all("i", class_=re.compile("StatsStory__stories-icon___"))


		for tmp in rating_i:
			tmp.name='span'
			tmp.string = ", ★"
		for tmp in reads_i:
			tmp.name='span'
			tmp.string = ", 📊"
		for tmp in favourites_i:
			tmp.name='span'
			tmp.string = ", ❤"
		for tmp in comments_i:
			tmp.name='span'
			tmp.string = ", 💬"
		for tmp in lists_i:
			tmp.name='span'
			tmp.string = ", ☵"

		for bad in soup.find_all("svg"):
			bad.decompose()

		return soup.prettify()

