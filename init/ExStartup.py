
import modules.WebRequest
import json
import copy
import logging
import os.path

import main

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


		attrs = [
			'version',
			'name',
			'value',
			'port',
			'port_specified',
			'domain',
			'domain_specified',
			'domain_initial_dot',
			'path',
			'path_specified',
			'secure',
			'expires',
			'discard',
			'comment',
			'comment_url',
			'rest',
			'rfc2109',
		]

		self.log.info("Fixing cookies")
		for cookie in self.wg.cj:
			if "ipb_member_id" in cookie.name or "ipb_pass_hash" in cookie.name:

				dup = copy.copy(cookie)
				dup.domain = 'exhentai.org'
				self.wg.addCookie(dup)

				if "ipb_member_id" in cookie.name:
					# Crude, CRUDE hack to install the gallery view settings
					# Specificaly, rc_3 which sets the per-page items to 200, rather then 25 (requires a hath perk)
					dup1 = copy.copy(cookie)
					dup2 = copy.copy(cookie)

					dup2.domain = 'exhentai.org'
					dup1.name  = 'uconfig'
					dup2.name  = 'uconfig'
					dup1.value = 'tl_m-uh_y-tr_2-ts_m-prn_y-dm_l-ar_0-xns_0-rc_3-rx_0-ry_0-cs_a-to_a-pn_0-sc_0-cats_0-ms_n-mt_n-sa_y-oi_n-qb_n-tf_n-hp_-hk_-xl_'
					dup2.value = 'tl_m-uh_y-tr_2-ts_m-prn_y-dm_l-ar_0-xns_0-rc_3-rx_0-ry_0-cs_a-to_a-pn_0-sc_0-cats_0-ms_n-mt_n-sa_y-oi_n-qb_n-tf_n-hp_-hk_-xl_'
					self.wg.addCookie(dup1)
					self.wg.addCookie(dup2)



	def doSetup(self):
		self.checkLogin()


class InitSystem_ExScraper(ExInit):

	name = 'WebRequest'

	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)

		self.calls = {
			'init'               : self.doSetup
		}
