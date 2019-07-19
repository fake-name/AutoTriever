
import urllib.parse
import logging
import bs4
import WebRequest

from . import ProcessorBase

class CrNFixer(ProcessorBase.ProcessorBase):

	log_name = "Main.Processor.CrN-Fixer"


	@staticmethod
	def wants_url(lowerspliturl, mimetype):
		if 'text/html' not in mimetype:
			return False

		return lowerspliturl.netloc.endswith("creativenovels.com")

	def preprocess_content(self, lowerspliturl, mimetype, contentstr):
		if isinstance(contentstr, bytes):
			contentstr = bs4.UnicodeDammit(contentstr).unicode_markup

		if 'chapter_list_novel_page' in contentstr:
			self.log.info("Chapter list page. Inserting ToC")
			contentstr = self._render_crn_toc(contentstr)

		contentstr = self._cleanup_content(contentstr)

		return contentstr


	###################################################################################################
	# CrN garbage
	###################################################################################################


	def _cleanup_content(self, contentstr):

		soup = WebRequest.as_soup(contentstr)
		next_chp_links = soup.find_all("a", class_='nextkey')
		prev_chp_links = soup.find_all("a", class_='prevkey')

		for tag in next_chp_links:
			tag.string = "Next chapter"
		for tag in prev_chp_links:
			tag.string = "Previous chapter"

		for bogus in soup.find_all("div", class_='x-modal-content'):
			bogus.decompose()
		for bogus in soup.find_all("div", class_='wpdiscuz_unauth'):
			bogus.decompose()
		for bogus in soup.find_all("div", class_='wpd-default'):
			bogus.decompose()
		for bogus in soup.find_all("div", class_='imagepost'):
			bogus.decompose()
		for bogus in soup.find_all("div", class_='donation'):
			bogus.decompose()
		for bogus in soup.find_all("form", class_='x-search'):
			bogus.decompose()
		for bogus in soup.find_all("ul", class_='x-menu'):
			bogus.decompose()
		for bogus in soup.find_all("div", class_='comments-area'):
			bogus.decompose()
		for bogus in soup.find_all("div", class_='respond'):
			bogus.decompose()
		for bogus in soup.find_all("div", class_='x-bar-space-v'):
			bogus.decompose()
		for bogus in soup.find_all("div", class_='e23-20'):
			bogus.decompose()
		for bogus in soup.find_all("button"):
			bogus.decompose()
		for bogus in soup.find_all("a", id='wpdUserContentInfoAnchor'):
			bogus.decompose()
		for bogus in soup.find_all("div", id='wpdUserContentInfo'):
			bogus.decompose()

		appends = []
		for item in soup.find_all('div', class_='togglepost'):
			# print("found append")
			appends.append(item.extract())

		tgtdiv = soup.find("article", class_='post')

		if tgtdiv:
			tgtdiv = tgtdiv.parent.parent
			tgtdiv.append(soup.new_tag('hr'))
			for append in appends:
				# print("Appending:", append)
				tgtdiv.append(append)

		# There should only ever be one of these.
		for mature_div in soup.find_all("div", class_='include_content_rating'):
			for item in mature_div.find_all('div', class_='list-group-item'):
				item.decompose()

		return soup.prettify()

	def _render_crn_toc(self, content):


		soup = WebRequest.as_soup(content)
		toc_goes_here = soup.find("div", id='chapter_list_novel_page')
		if toc_goes_here and toc_goes_here.get('class', None):
			classid = toc_goes_here.get('class', None)
			if len(classid) != 1:
				self.log.warning("ToC div class is empty!")
				return soup.prettify()

			cid = classid[0]
			post_params = {
				"action"  : "crn_chapter_list",
				"view_id" : cid
			}
			extra_headers = {
				"x-requested-with" : "XMLHttpRequest",
			}

			cdat = self.wg.getpage("https://creativenovels.com/wp-admin/admin-ajax.php", postData=post_params, addlHeaders=extra_headers)

			'''
			What the ever-loving-fuck format is this? This is why we have fucking json, peeps!

			Decoder:
				LoadAjax3 = 0;
				if (ret_data.indexOf("success") > -1) {
					try {
						var define = ret_data.split('.define.');
						var html_body = "";
						var data = define[1].split('.end_data.');
						data.forEach(function(element) {
							if (element != "" && element != undefined) {
								var in_data = element.split('.data.');
								html_body += '<a href="' + in_data[0] + '"><div data-date="' + in_data[2] + '" data-lock="' + in_data[3] + '" class="post_url">' + in_data[1] + '</div></a>'
							}
						});
						ChapterLoaded1 = 1;
						document.getElementById("chapter_list_novel_page").innerHTML = '<div class="flipflopindexundo" onclick="sortIndex()"></div><input type="text" id="myInputChapter" onkeyup="myFunctionChapterSorter()" placeholder="    Search for chapter.." title="search for chapter"><br /><div class="post_box">' + html_body + '</div>'
					} catch (e) {}
				} else {}

			'''

			if 'success' not in cdat:
				self.log.warning("No success flag in response!")
				return soup.prettify()

			contents_table = soup.new_tag("table")

			dummy_prefix, data_sec = cdat.split(".define.", 1)
			data_segs = data_sec.split('.end_data.')
			for seg in data_segs:
				data = seg.split(".data.")
				if len(data) != 4:
					continue

				clink, cdesc, cdate, state = data

				if state != 'available':
					continue

				row = soup.new_tag("tr")

				cdesc = cdesc.replace("–", "-")
				cdesc = cdesc.replace("&#8211;", "-")

				td = soup.new_tag("td")
				row.append(td)
				newlink = soup.new_tag("a", href=clink)
				newlink.string = cdesc
				td.append(newlink)

				td = soup.new_tag("td")
				row.append(td)
				td.string = cdate

				contents_table.append(row)


			# print("Contents table:", contents_table)
			toc_goes_here.replace_with(contents_table)



		return soup.prettify()





