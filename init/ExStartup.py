
import modules.WebRequest
import json
import copy
import logging
import os.path

import main


def loadSettings():

	settings = None

	sPaths = ['./settings.json', '../settings.json']

	for sPath in sPaths:
		if not os.path.exists(sPath):
			continue
		with open('./settings.json', 'r') as fp:
			settings = json.load(fp)

	if not settings:
		raise ValueError("No settings.json file found!")

	return settings


class ExInit():



	def __init__(self):
		self.wg = modules.WebRequest.WebGetRobust(logPath="Main.SadPanda.Web")
		self.log = logging.getLogger('Main.SadPanda.Interface')

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
		if "Username or password incorrect" in getPage:
			self.log.error("Login failed!")
			with open("pageTemp.html", "wb") as fp:
				fp.write(getPage)
		elif "You are now logged in as:" in getPage:
			self.log.info("Logged in successfully!")

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


	def doSetup(self):
		self.checkLogin()


class InitSystem_ExScraper(ExInit):

	name = 'WebRequest'

	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)

		self.calls = {
			'init'               : self.doSetup
		}
