#!/usr/bin/python3

import time
import os.path
import random
import socket
import urllib.parse
import http.cookiejar
import bs4

import ChromeController

# THIS IS COMPLETELY BROKEN ATM!


class WebGetCrMixin(object):
	# creds is a list of 3-tuples that gets inserted into the password manager.
	# it is structured [(top_level_url1, username1, password1), (top_level_url2, username2, password2)]
	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)

		self.cr_driver = None


	def _initChrome(self):
		crbin = "google-chrome"
		self._cr = ChromeController.ChromeRemoteDebugInterface(crbin)

	def _syncIntoChrome(self):
		# TODO
		pass

	def _syncOutOfChrome(self):
		for cookie in self.cr_driver.get_cookies():
			self.addSeleniumCookie(cookie)


	def getItemChrome(self, itemUrl):
		self.log.info("Fetching page for URL: '%s' with PhantomJS" % itemUrl)

		if not self.cr_driver:
			self._initChrome()
		self._syncIntoChrome()

		with load_delay_context_manager(self.cr_driver):
			self.cr_driver.get(itemUrl)
		time.sleep(3)

		fileN = urllib.parse.unquote(urllib.parse.urlparse(self.cr_driver.current_url)[2].split("/")[-1])
		fileN = bs4.UnicodeDammit(fileN).unicode_markup

		self._syncOutOfChrome()

		# Probably a bad assumption
		mType = "text/html"

		# So, self.cr_driver.page_source appears to be the *compressed* page source as-rendered. Because reasons.
		source = self.cr_driver.execute_script("return document.getElementsByTagName('html')[0].innerHTML")

		assert source != '<head></head><body></body>'

		source = "<html>"+source+"</html>"
		return source, fileN, mType



	def getHeadTitleChromium(self, url, referrer):
		self.getHeadChromium(url, referrer)
		ret = {
			'url'   : self.cr_driver.current_url,
			'title' : self.cr_driver.title,
		}
		return ret

	def getHeadChromium(self, url, referrer):
		self.log.info("Getting HEAD with PhantomJS")

		if not self.cr_driver:
			self._initChrome()
		self._syncIntoChrome()

		def try_get(loc_url):
			tries = 3
			for x in range(9999):
				try:
					self.cr_driver.get(loc_url)
					time.sleep(random.uniform(2, 6))
					return
				except socket.timeout as e:
					if x > tries:
						raise e

		try_get(referrer)
		try_get(url)

		self._syncOutOfCrWebDriver()

		return self.cr_driver.current_url

	def addSeleniumCookie(self, cookieDict):
		'''
		Install a cookie exported from a selenium webdriver into
		the active opener
		'''
		# print cookieDict
		cookie = http.cookiejar.Cookie(
				version            = 0,
				name               = cookieDict['name'],
				value              = cookieDict['value'],
				port               = None,
				port_specified     = False,
				domain             = cookieDict['domain'],
				domain_specified   = True,
				domain_initial_dot = False,
				path               = cookieDict['path'],
				path_specified     = False,
				secure             = cookieDict['secure'],
				expires            = cookieDict['expiry'] if 'expiry' in cookieDict else None,
				discard            = False,
				comment            = None,
				comment_url        = None,
				rest               = {"httponly":"%s" % cookieDict['httponly']},
				rfc2109            = False
			)

		self.addCookie(cookie)


	def __del__(self):

		if self.cr_driver != None:
			self.cr_driver.quit()


	def stepThroughCloudFlare_cr(self, url, titleContains='', titleNotContains=''):
		'''
		Use Selenium+PhantomJS to access a resource behind cloudflare protection.

		Params:
			``url`` - The URL to access that is protected by cloudflare
			``titleContains`` - A string that is in the title of the protected page, and NOT the
				cloudflare intermediate page. The presence of this string in the page title
				is used to determine whether the cloudflare protection has been successfully
				penetrated.

		The current WebGetRobust headers are installed into the selenium browser, which
		is then used to access the protected resource.

		Once the protected page has properly loaded, the cloudflare access cookie is
		then extracted from the selenium browser, and installed back into the WebGetRobust
		instance, so it can continue to use the cloudflare auth in normal requests.

		'''

		if (not titleContains) and (not titleNotContains):
			raise ValueError("You must pass either a string the title should contain, or a string the title shouldn't contain!")

		if titleContains and titleNotContains:
			raise ValueError("You can only pass a single conditional statement!")


		self.log.info("Attempting to access page through cloudflare browser verification.")

		dcap = dict(DesiredCapabilities.PHANTOMJS)
		wgSettings = dict(self.browserHeaders)

		# Install the headers from the WebGet class into phantomjs
		dcap["phantomjs.page.settings.userAgent"] = wgSettings.pop('User-Agent')
		for headerName in wgSettings:
			dcap['phantomjs.page.customHeaders.{header}'.format(header=headerName)] = wgSettings[headerName]

		driver = selenium.webdriver.Chromium(desired_capabilities=dcap)
		driver.set_window_size(1024, 768)

		driver.get(url)

		if titleContains:
			condition = EC.title_contains(titleContains)
		elif titleNotContains:
			condition = title_not_contains(titleNotContains)
		else:
			raise ValueError("Wat?")


		try:
			WebDriverWait(driver, 20).until(condition)
			success = True
			self.log.info("Successfully accessed main page!")
		except TimeoutException:
			self.log.error("Could not pass through cloudflare blocking!")
			success = False
		# Add cookies to cookiejar

		for cookie in driver.get_cookies():
			self.addSeleniumCookie(cookie)
			#print cookie[u"value"]

		self.__syncCookiesFromFile()

		return success


