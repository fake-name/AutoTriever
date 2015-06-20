
# -*- coding: utf-8 -*-

import modules.WebRequest

import re

import threading

import urllib.error
import traceback


import copy
import logging
import main


class ExScrapeError(Exception):
	pass
class OutOfCreditsException(ExScrapeError):
	pass
class GalleryDeletedException(ExScrapeError):
	pass
class LoginException(ExScrapeError):
	pass

class ExContentLoader(object):


	loggerPath = "Main.SadPanda.Cl"
	pluginName = "SadPanda Content Retreiver"

	urlBase = "http://exhentai.org/"



	def __init__(self):

		thName = threading.current_thread().name
		if "-" in thName:
			logPath = "Main.Thread-{num}.SadPanda.Cl".format(num=thName.split("-")[-1])
		else:
			logPath = 'Main.SadPanda.Cl'

		self.log = logging.getLogger(logPath)
		self.wg = modules.WebRequest.WebGetRobust(logPath=logPath+".Web")

		self.log = logging.getLogger(self.loggerPath)
		self.log.info("Loading %s Runner", self.pluginName)

		self.settings = main.loadSettings()

	# -----------------------------------------------------------------------------------
	# Login Management tools
	# -----------------------------------------------------------------------------------


	def checkLogin(self):

		checkPage = self.wg.getpage(r"https://forums.e-hentai.org/index.php?")
		if "Logged in as" in checkPage:
			self.log.info("Still logged in")
			return
		else:
			self.log.info("Whoops, need to get Login cookie")

		logondict = {
			"UserName"   : self.settings['sadPanda']["login"],
			"PassWord"   : self.settings['sadPanda']["passWd"],
			"referer"    : "https://forums.e-hentai.org/index.php?",
			"CookieDate" : "Log me in",
			"b"          : '',
			"bt"         : '',
			"submit"     : "Log me in"
			}


		getPage = self.wg.getpage(r"https://forums.e-hentai.org/index.php?act=Login&CODE=01", postData=logondict)
		if "You are now logged in as:" in getPage:
			self.log.info("Logged in successfully!")
		else:
			self.log.error("Login failed!")
			raise LoginException("Login failed! Is your login data valid?")

		self.permuteCookies()
		self.wg.saveCookies()

	# So exhen uses some irritating cross-site login hijinks.
	# Anyways, we need to copy the cookies for e-hentai to exhentai,
	# so we iterate over all cookies, and duplicate+modify the relevant
	# cookies.
	def permuteCookies(self):
		self.log.info("Fixing cookies")
		for cookie in self.wg.cj:
			if "ipb_member_id" in cookie.name or "ipb_pass_hash" in cookie.name:

				dup = copy.copy(cookie)
				dup.domain = 'exhentai.org'

				self.wg.addCookie(dup)


	# MOAR checking. We load the root page, and see if we have anything.
	# If we get an error, it means we're being sadpanda'ed (because it serves up a gif
	# rather then HTML, which causes getSoup() to error), and we should abort.
	def checkExAccess(self):
		try:
			self.wg.getSoup(self.urlBase)
			return True
		except ValueError:
			return False


	# -----------------------------------------------------------------------------------
	# The scraping parts
	# -----------------------------------------------------------------------------------




	def getDownloadPageUrl(self, inSoup):
		dlA = inSoup.find('a', onclick=re.compile('archiver.php'))

		clickAction = dlA['onclick']
		clickUrl = re.search("(http://exhentai.org/archiver.php.*)'", clickAction)
		return clickUrl.group(1)


	def getDownloadInfo(self, sourceUrl):
		self.log.info("Retreiving item: %s", sourceUrl)

		try:
			soup = self.wg.getSoup(sourceUrl, addlHeaders={'Referer': self.urlBase})
		except:
			self.log.critical("No download at url %s!", sourceUrl)
			raise ExScrapeError("Invalid webpage '%s'", sourceUrl)

		if "This gallery has been removed, and is unavailable." in soup.get_text():
			self.log.info("Gallery deleted.")
			raise GalleryDeletedException("Gallery at '%s' has been deleted!" % (sourceUrl))

		dlPage = self.getDownloadPageUrl(soup)

		return dlPage


	def extractGpCost(self, soup):
		cost = -2
		main = soup.find('div', id='db')
		for div in [div for div in main.find_all('div') if div.get_text().strip()]:
			text = div.get_text().strip()
			if 'Download Cost:' in text and 'GP' in text:
				text = text.split(":")[-1]
				text = text.split("GP")[0]
				text = text.replace(",", "")
				text = text.replace(".", "")
				text = text.strip()
				cost = int(text)


		if cost > 0:
			self.log.info("Gallery cost: %s GP", cost)
		else:
			self.log.error("Could not extract gallery cost!")
			return -2
		return cost


	def getDownloadUrl(self, dlPageUrl, referrer):

		soup = self.wg.getSoup(dlPageUrl, addlHeaders={'Referer': referrer})

		gpCost = self.extractGpCost(soup)

		if 'Insufficient funds'.lower() in str(soup).lower():
			raise OutOfCreditsException("Out of credits. Cannot download!")

		if 'Pressing this button will immediately deduct funds' in soup.get_text():
			self.log.info("Accepting download.")
			acceptForm = soup.find('form')
			formPostUrl = acceptForm['action']
			soup = self.wg.getSoup(formPostUrl, addlHeaders={'Referer': referrer}, postData={'dlcheck': 'Download Archive'})
		else:
			self.log.warn("Already accepted download?")



		contLink = soup.find('p', id='continue')
		if not contLink:
			self.log.error("No link found!")
			self.log.error("Page Contents: '%s'", soup)

			raise ExScrapeError("Could not find download link on page '%s'!" % (dlPageUrl, ))

		downloadUrl = contLink.a['href']+"?start=1"

		return downloadUrl, gpCost

	def doDownload(self, downloadUrl, sourceUrl):

		downloadUrl, gpCost = self.getDownloadUrl(downloadUrl, sourceUrl)
		fCont, fName = self.wg.getFileAndName(downloadUrl)


		self.log.info("Downloaded filename: %s.", fName)

		response = {
			u'success'     : True,
			u'gpcost'      : gpCost,
			u'fileN'       : fName,
			u'fileC'       : fCont,
			u'cancontinue' : True
		}
		return response


	def getLink(self, sourceUrl):
		'''
		Response codes:

			`success`     - Self Explanitory. Boolean of whether the retreival was successful.
			`error`       - Error string. Current error types are "gdeleted" (gallery deleted),
								"credits" (client out of credits),
								"urlerror" (error accessing file (generally a HTTP error, or something is really broken))
			`traceback`   - In the case of an exception being thrown in the client, this will contain the traceback of the thrown
								exception, as a string.
			`cancontinue` - Boolean, can the client continue to process galleries. In the case of deleted galleries
								or transient URLerrors, the problem is not client-side, so the client will keep
								running. If the client is out of GP, it will exit, and return `cancontinue` = False

		For Successful scrape:
			`gpcost`      - Cost of downloading gallery in GP
			`fileN`       - The name of the downloaded file
			`fileC`       - The file contents, as a byte string


		'''
		try:
			downloadUrl = self.getDownloadInfo(sourceUrl)

			response = self.doDownload(downloadUrl, sourceUrl)

		except urllib.error.URLError:
			response = {
				u'success'     : False,
				u'error'       : u"urlerror",
				u'traceback'   : traceback.format_exc(),
				u'cancontinue' : True
			}
			self.log.error("Failure retreiving content for link %s", sourceUrl)
			self.log.error("Traceback: %s", traceback.format_exc())
			return response


		except GalleryDeletedException:
			response = {
				u'success'     : False,
				u'error'       : u"gdeleted",
				u'traceback'   : traceback.format_exc(),
				u'cancontinue' : True
			}
			self.log.error("Gallery for link has been deleted %s", sourceUrl)
			self.log.error("Traceback: %s", traceback.format_exc())
			return response

		except OutOfCreditsException:
			response = {
				u'success'     : False,
				u'error'       : u"credits",
				u'traceback'   : traceback.format_exc(),
				u'cancontinue' : False
			}
			self.log.error("Client is out of credits!")
			self.log.error("Traceback: %s", traceback.format_exc())
			return response


		except ExScrapeError:
			response = {
				u'success'     : False,
				u'error'       : u"credits",
				u'traceback'   : traceback.format_exc(),
				u'cancontinue' : False
			}
			self.log.error("Unknown exception on page '%s'!", sourceUrl)
			self.log.error("Traceback: %s", traceback.format_exc())
			return response

		return response



class PluginInterface_ExContentLoader(ExContentLoader):

	name = 'ExContentLoader'

	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)

		self.checkLogin()



		self.calls = {
			'getpage'               : self.wg.getpage,
			'fetchcontent'          : self.getLink,
		}


