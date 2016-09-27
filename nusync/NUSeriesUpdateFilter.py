
import re
import calendar
import traceback
import datetime
import time
import json
import random
import selenium.common.exceptions
import bs4

import sqlalchemy.exc

import mmh3
from . import LogBase
from  . import database as db

from . import AmqpInterface
from util import WebRequest

MIN_RATING = 5

########################################################################################################################
#
#	##     ##    ###    #### ##    ##     ######  ##          ###     ######   ######
#	###   ###   ## ##    ##  ###   ##    ##    ## ##         ## ##   ##    ## ##    ##
#	#### ####  ##   ##   ##  ####  ##    ##       ##        ##   ##  ##       ##
#	## ### ## ##     ##  ##  ## ## ##    ##       ##       ##     ##  ######   ######
#	##     ## #########  ##  ##  ####    ##       ##       #########       ##       ##
#	##     ## ##     ##  ##  ##   ###    ##    ## ##       ##     ## ##    ## ##    ##
#	##     ## ##     ## #### ##    ##     ######  ######## ##     ##  ######   ######
#
########################################################################################################################


class NUSeriesUpdateFilter(LogBase.LoggerMixin):

	loggerPath = "Main.NovelUpdates.Series"

	# This plugin doesn't need AMQP connectivity at all.
	_needs_amqp = False


	def __init__(self, db_sess, settings):
		super().__init__()

		self.settings = settings
		# self.db_sess = db_sess
		if settings and 'RABBIT_LOGIN' in settings:
			self.amqp = AmqpInterface.RabbitQueueHandler(settings)
		else:
			self.amqp = None
		self.wg = WebRequest.WebGetRobust(cloudflare=True)


##################################################################################################################################
##################################################################################################################################
##################################################################################################################################


	def extractSeriesReleases(self, currentUrl, soup):

		container = soup.find('div', class_='l-content')

		assert container is not None

		release_tables = container.find_all('table', class_='tablesorter')

		# print("Release tables:", release_tables)

		releases = []
		for table_div in release_tables:
			for item in table_div.find_all("tr"):
				tds = item.find_all('td')
				if len(tds) == 3:
					series, release, group = tds
					linkas = release.find_all('a', class_='chp-release')
					sname = series.get_text().strip()
					gname = group.get_text().strip()
					for link in linkas:
						release = {
							'seriesname'       : sname,
							'releaseinfo'      : link.get_text().strip(),
							'groupinfo'        : gname,
							'referrer'         : currentUrl,
							'outbound_wrapper' : link['href'],
							'actual_target'    : None,

							'client_id'        : self.settings['clientid'],
							'client_key'       : self.settings['client_key'],
						}
						# print("Link: ", link['href'])
						releases.append(release)

		return releases


	def fetchPage(self, url):
		content, dummy_fname, dummy_mime = self.wg.getItemPhantomJS(url)
		return content

	def processPage(self, url, content):
		soup = WebRequest.as_soup(content)
		releases = self.extractSeriesReleases(url, soup)
		relcnt = len(releases)
		if relcnt > 0:
			self.log.info("Found %s Releases.", relcnt)
		else:
			self.log.error("No releases found!")

		return releases

	def qualifyLink(self, release):

		print("Qualifying: '%s'" % release)

		# have = self.db_sess.query(db.LinkWrappers)                                   \
		# 	.filter(db.LinkWrappers.outbound_wrapper == release['outbound_wrapper']) \
		# 	.filter(db.LinkWrappers.seriesname == release['seriesname'])             \
		# 	.scalar()
		# if have:
		# 	release['actual_target'] = have.actual_target
		# 	self.log.info("Have: %s (%s, %s)", have, release['outbound_wrapper'], release['seriesname'])
		# 	self.amqp.putRow(have)
		# 	return False  # Don't sleep, since we didn't do a remote fetch.

		basepage = release['referrer']
		if not self.wg.pjs_driver:
			self.wg.getItemPhantomJS(basepage)
			time.sleep(random.randint(3, 9))
		elif self.wg.pjs_driver.current_url.rstrip("/") != basepage.rstrip("/"):
				self.log.info("Need to resolve '%s' (current URL: '%s')",
						basepage.rstrip("/"),
						self.wg.pjs_driver.current_url.rstrip("/")
					)
				self.wg.pjs_driver.get(basepage)
				time.sleep(random.randint(3, 9))
		# else:
		# 	print("already navigated to the correct page.")

		selector = "a[href*='" + release['outbound_wrapper'] + "']"
		# print("Selector: ", selector)

		content = self.wg.pjs_driver.execute_script("return document.getElementsByTagName('html')[0].innerHTML")
		if not release['outbound_wrapper'] in content:
			return None
		# print(release['outbound_wrapper'] + " in page:", release['outbound_wrapper'] in content)

		linkbutton = self.wg.pjs_driver.find_element_by_css_selector(selector)
		if not linkbutton:
			self.log.error("Can't find link to release with selector '%s'", selector)

		# print("Linkbutton:", linkbutton)
		# Ignore the non-visible elements. Nice try tho, guy!
		try:
			visible = linkbutton.is_displayed()
		except selenium.common.exceptions.WebDriverException:
			# print("Wut?")
			raise
		if not visible:
			return None


		linkbutton.click()

		time.sleep(3)

		release['actual_target'] = self.wg.pjs_driver.current_url

		# new = db.LinkWrappers(
		# 	seriesname       = release['seriesname'],
		# 	releaseinfo      = release['releaseinfo'],
		# 	groupinfo        = release['groupinfo'],
		# 	referrer         = release['referrer'],
		# 	outbound_wrapper = release['outbound_wrapper'],
		# 	actual_target    = self.wg.pjs_driver.current_url,
		# 	addtime          = datetime.datetime.now(),
		# 	)

		# self.db_sess.add(new)
		# self.db_sess.commit()
		if self.amqp:
			self.amqp.putRow(release)

		release['actual_target'] = self.wg.pjs_driver.current_url

		self.log.info("New entry!")
		self.log.info("	Series:   '%s'", release['seriesname'])
		self.log.info("	Release:  '%s'", release['releaseinfo'])
		self.log.info("	Group:    '%s'", release['groupinfo'])
		self.log.info("	Outbound: '%s'", release['outbound_wrapper'])
		self.log.info("	Referrer: '%s'", release['referrer'])
		self.log.info("	Real:     '%s'", self.wg.pjs_driver.current_url)

		# self.wg.pjs_driver.execute_script("window.history.go(-1)")
		self.log.info("Attempting to go back to source page")
		for dummy_x in range(5):
			if self.wg.pjs_driver.current_url.rstrip("/") != basepage.rstrip("/"):
				self.wg.pjs_driver.back()
				time.sleep(2)
				self.log.info("	%s -> %s", self.wg.pjs_driver.current_url.rstrip("/"), basepage.rstrip("/"))
		if self.wg.pjs_driver.current_url.rstrip("/") == basepage.rstrip("/"):
			self.log.info("Returned back to base-page.")
		else:
			self.log.error("Could not use back nav control to return to base-page!")

		return True

	def qualifyLinks(self, releaselist):
		limit = random.randint(5, 40)
		random.shuffle(releaselist)
		for release in releaselist:

			# Hash the series name, modulo number of clients,
			# and pick the series that match the active client.
			# This makes each client "picky" about what series
			# it "reads".
			# chp_hash = mmh3.hash(release['seriesname'])
			# chp_hash = chp_hash % self.settings['client_count']
			# if chp_hash != self.settings['client_number']:
			# 	self.log.info("This client doesn't 'want' entries for series '%s'", release['seriesname'])
			# 	continue

			sleep = True
			try:
				sleep = self.qualifyLink(release)
			except selenium.common.exceptions.WebDriverException:
				self.log.error("Error when resolving outbound referrer!")
				for line in traceback.format_exc().split("\n"):
					self.log.error(line)

				raise

			if sleep:

				# Fetch n items per hour max
				limit = limit - 1
				if limit <= 0:
					return

				sleeptime = int(random.triangular(15, 20*60, 3*60))
				for x in range(sleeptime):
					if x % 15 == 0:
						self.log.info("NU Interface - Sleeping %s seconds (%s remaining)", sleeptime, sleeptime-x)
					time.sleep(1)


	def handlePage(self, url):
		if self.wg == None:
			self.wg = WebRequest.WebGetRobust(cloudflare=True)
		try:
			rawpg = self.fetchPage(url)
			releases = self.processPage(url, rawpg)
			fqreleases = self.qualifyLinks(releases)
		finally:
			try:
				self.log.info("Attempting to shut down PhantomJS")
				self.log.info("PhantomJS instance closed.")
				self.wg.pjs_driver.quit()
			except Exception:
				self.log.error("Issue when shutting down PhantomJS Instance.")
				for line in traceback.format_exc().split("\n"):
					self.log.error(line)
			self.log.info("Dropping WebRequest.")
			self.wg = None


def test():
	print("Test mode!")
	import deps.logSetup
	import multiprocessing
	deps.logSetup.initLogging()

	# c_lok = cookie_lock = multiprocessing.Lock()
	# engine = WebMirror.Engine.SiteArchiver(cookie_lock=c_lok)
	settings = {
		'clientid'   : "Wat",
		'client_key' : "Wat",
	}

	test = {
		'actual_target': None,
		'client_id': 'scrape-worker-2',
		'client_key': 'urn:uuid:d1fb79da-66a6-4deb-9af1-c5309fa51b59',
		'seriesname': 'Kumo Desu ga, Nani ka?',
		'referrer': 'https://www.novelupdates.com',
		'groupinfo': 'Raising the Dead',
		'releaseinfo': 'situation of blowsituation of blow',
		'outbound_wrapper': 'http://www.novelupdates.com/extnu/279638/'}

	uf = NUSeriesUpdateFilter(None, settings)
	print(uf)
	uf.handlePage("http://www.novelupdates.com/")
	# uf.qualifyLink(test)
	# engine.dispatchRequest(testJobFromUrl('http://www.novelupdates.com/'))

	# for x in range(0, 180):
	# 	engine.dispatchRequest(testJobFromUrl('http://www.novelupdates.com/?pg={num}'.format(num=x)))

	# engine.dispatchRequest(testJobFromUrl('http://www.novelupdates.com/?pg=1'))
	# engine.dispatchRequest(testJobFromUrl('http://www.novelupdates.com/?pg=2'))
	# engine.dispatchRequest(testJobFromUrl('http://www.novelupdates.com/?pg=3'))
	# engine.dispatchRequest(testJobFromUrl('http://www.novelupdates.com/?pg=4'))


if __name__ == "__main__":
	print("Testing")
	test()

