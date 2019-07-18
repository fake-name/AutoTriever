
import urllib.parse
import logging
import bs4
import WebRequest

from autotriever.modules.SmartFetch import ProcessorBase

class CrNFixer(ProcessorBase.ProcessorBase):

	log = logging.getLogger("Main.CrN-Fixer")

	def __init__(self, wg:WebRequest.WebGetRobust):
		super().__init__()
		self.wg = wg


	def smartGetItem(self, itemUrl, *args, **kwargs):
		content, fileN, mType = self.wg.getItem(itemUrl=itemUrl, *args, **kwargs)

		if 'text/html' in mType:
			content = self._check_response(itemUrl, content)

		return content, fileN, mType


	###################################################################################################
	# Dispatcher
	###################################################################################################

	def _check_response(self, url, contentstr):
		netloc = urllib.parse.urlsplit(url).netloc

		if netloc.lower().endswith("creativenovels.com"):
			self.log.info("Creative Novel preprocessor wants to manipulate the response")
			contentstr = self._create_novels_stupid(url, contentstr)

		return contentstr

	###################################################################################################
	# CrN garbage
	###################################################################################################

	def _create_novels_stupid(self, url, content):
		if 'chapter_list_novel_page' in content:
			self.log.info("Chapter list page. Inserting ToC")
			content = self.__render_crn_toc(content)

		return content

	def __render_crn_toc(self, content):

		if isinstance(content, bytes):
			content = bs4.UnicodeDammit(content).unicode_markup

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


				td = soup.new_tag("td")
				row.append(td)
				newlink = soup.new_tag("a", href=clink)
				newlink.string = cdesc
				td.append(newlink)

				td = soup.new_tag("td")
				row.append(td)
				td.string = cdate

				contents_table.append(row)


			print("Contents table:", contents_table)
			toc_goes_here.replace_with(contents_table)



		return soup.prettify()





