
import scheduled.model            as model
import autotriever.amqp_connector as amqp_connector
import autotriever.load_settings  as load_settings

import os.path
import site
import datetime
import logging
import random
import time
import traceback
import urllib.error
import WebRequest

wd = os.path.abspath(os.getcwd())
relp = "./scheduled/NuUpdate"
module_path = os.path.join(wd, relp)
abs_module_path = os.path.abspath(module_path)
site.addsitedir(abs_module_path)

import WebMirror.OutputFilters.Nu.NUHomepageFilter   as NUHomepageFilter
import WebMirror.OutputFilters.Nu.NuSeriesPageFilter as NuSeriesPageFilter
from WebMirror.OutputFilters.util.TitleParsers import title_from_html



REFETCH_INTERVAL = datetime.timedelta(days=5)
FETCH_ATTEMPTS   = 3
SINGLETON_WG     = WebRequest.WebGetRobust(use_global_tab_pool=False)

HOMEPAGE_URL = "https://www.novelupdates.com"

class NuPageUpdater():
	def __init__(self):
		self.log = logging.getLogger("Main.NuMonitor")

		settings = load_settings.loadSettings()
		sslopts  = load_settings.findCert()

		# self.connector = amqp_connector.Connector(
		# 				userid             = settings["RABBIT_LOGIN"],
		# 				password           = settings["RABBIT_PASWD"],
		# 				host               = settings["RABBIT_SRVER"],
		# 				virtual_host       = settings["RPC_RABBIT_VHOST"],

		# 				task_queue         = settings.get("RPC_RABBIT_TASK_QUEUE_NAME",     "task.q"),
		# 				response_queue     = settings.get("RPC_RABBIT_RESPONSE_QUEUE_NAME", "response.q"),
		# 				task_exchange      = settings.get("RPC_RABBIT_TASK_EXCHANGE",       "tasks.e"),
		# 				response_exchange  = settings.get("RPC_RABBIT_RESPONSE_EXCHANGE",   "resps.e"),

		# 				ssl                = sslopts,
		# 				prefetch           = 2,
		# 				synchronous        = True,
		# 				task_exchange_type = "direct",
		# 				durable            = True, )

		# self.log.info("AMQP Connection initialized. Entering runloop!")


	def load_recent(self):
		with model.session_context() as sess:
			pass




	def go(self):
		recent = self.load_recent()





class NuMonitor():
	def __init__(self):

		self.log = logging.getLogger("Main.NuMonitor")

		self.hpf = NUHomepageFilter.NuHomepageFilter(
				pageUrl   = None,
				pgContent = None,
				type      = None,
				db_sess   = None,
			)
		self.spf = NuSeriesPageFilter.NUSeriesPageFilter(
				pageUrl   = None,
				pgContent = None,
				type      = None,
				db_sess   = None,
			)

		self.wg = SINGLETON_WG

		self.connector = amqp_connector.Connector(
						userid             = settings["RABBIT_LOGIN"],
						password           = settings["RABBIT_PASWD"],
						host               = settings["RABBIT_SRVER"],
						virtual_host       = settings["RPC_RABBIT_VHOST"],

						task_queue         = settings.get("RPC_RABBIT_TASK_QUEUE_NAME",     "task.q"),
						response_queue     = settings.get("RPC_RABBIT_RESPONSE_QUEUE_NAME", "response.q"),
						task_exchange      = settings.get("RPC_RABBIT_TASK_EXCHANGE",       "tasks.e"),
						response_exchange  = settings.get("RPC_RABBIT_RESPONSE_EXCHANGE",   "resps.e"),

						ssl                = sslopts,
						prefetch           = 2,
						synchronous        = True,
						task_exchange_type = "direct",
						durable            = True, )


	def __check_load_extnu(self, item, sess):


		have = sess.query(model.NuReleaseItem).filter(model.NuReleaseItem.outbound_wrapper == item["outbound_wrapper"]).scalar()
		if have:
			if have.actual_target:
				self.log.info("Already have outbound wrapper for URL '%s' resolved to '%s'", have.outbound_wrapper, have.actual_target)
				return
			if have.fetch_tries > FETCH_ATTEMPTS:
				self.log.info("Outbound wrapper failed for URL '%s' (%s tries)", have.outbound_wrapper, have.fetch_tries)
				return

			self.log.info("Retrying outbound wrapper for URL '%s' (try %s of %s)", have.outbound_wrapper, have.fetch_tries, FETCH_ATTEMPTS)

		else:
			have = model.NuReleaseItem(
					fetch_tries      = 0,
					seriesname       = item["seriesname"],
					releaseinfo      = item["releaseinfo"],
					groupinfo        = item["groupinfo"],
					referrer         = item["referrer"],
					outbound_wrapper = item["outbound_wrapper"],
					release_date     = item["release_date"],
					first_seen       = datetime.datetime.now(),
				)
			sess.add(have)

		# Don't dewaf
		old_autowaf = self.wg.rules['auto_waf']
		self.wg.rules['auto_waf'] = False
		try:
			content, _name, _mime, url = self.wg.getFileNameMimeUrl(have.outbound_wrapper, addlHeaders={'Referer': have.referrer})
			if url.startswith("https://www.novelupdates.com/extnu/"):
				raise RuntimeError("Failure when extracting NU referrer!")
			pg_title = title_from_html(content)

			have.actual_target    = url
			have.page_title       = pg_title

			self.log.info("URL '%s' resolved to '%s'", have.outbound_wrapper, have.actual_target)
			self.log.info("Page title: '%s'", pg_title)

		except WebRequest.WebGetException:
			self.log.info("URL '%s' failed to resolve (TL Group: %s. Series %s, chap: %s)", have.outbound_wrapper, have.groupinfo, have.seriesname, have.releaseinfo)
			for line in traceback.format_exc().split("\n"):
				self.log.error(line)
		except urllib.error.URLError:
			self.log.info("URL '%s' failed to resolve (TL Group: %s. Series %s, chap: %s)", have.outbound_wrapper, have.groupinfo, have.seriesname, have.releaseinfo)
			for line in traceback.format_exc().split("\n"):
				self.log.error(line)

		self.wg.rules['auto_waf'] = old_autowaf


		have.fetch_tries     += 1

		sess.commit()


		sleep = random.triangular(3,10,30)
		self.log.info("Sleeping %s", sleep)
		time.sleep(sleep)

	def __check_load_page(self, url, sess):


		item = sess.query(model.WebPages).filter(model.WebPages.url == url).scalar()
		was_new = False
		if item:
			if item.fetchtime > datetime.datetime.now() - REFETCH_INTERVAL:
				self.log.info("URL '%s' fetched within refetch interval (%s). Not fetching", url, REFETCH_INTERVAL)
				return
			else:
				self.log.info("Refetching URL '%s'", url)

		else:
			was_new = True
			self.log.info("URL '%s' is new!", url)
			item = model.WebPages(
					url          = url,
					addtime      = datetime.datetime.now(),
				)

		try:
			content, _name, mime, url = self.wg.getFileNameMimeUrl(url, addlHeaders={'Referer': HOMEPAGE_URL})
			item.state        = "complete"
			item.errno        = None
			item.mimetype     = mime
			item.is_text      = "text" in mime
			item.content      = content
			item.fetchtime    = datetime.datetime.now()

		except WebRequest.WebGetException:
			for line in traceback.format_exc().split("\n"):
				self.log.error(line)
			item.state        = "error"
			item.errno        = -1
			item.fetchtime    = datetime.datetime.now()

		except urllib.error.URLError:
			for line in traceback.format_exc().split("\n"):
				self.log.error(line)
			item.state        = "error"
			item.errno        = -1
			item.fetchtime    = datetime.datetime.now()


		if was_new:
			sess.add(item)

		sess.commit()


		pg_title = title_from_html(content)
		self.log.info("Fetched '%s' with title '%s'", url, pg_title)
		sleep = random.triangular(3,10,30)
		self.log.info("Sleeping %s", sleep)
		time.sleep(sleep)


	def fetch_update_series_pages(self, urls):
		with model.session_context() as sess:
			for url in urls:
				self.__check_load_page(url, sess)

	def fetch_update_releases(self, releases):

		with model.session_context() as sess:
			for release in releases:
				self.__check_load_extnu(release, sess)


	def go(self):

		print("hpf", self.hpf)
		print("spf", self.spf)


		with model.session_context() as sess:
			pass

		soup = self.wg.getSoup(HOMEPAGE_URL)

		ref_pages, releases = self.hpf.extractSeriesReleases(HOMEPAGE_URL, soup)
		self.fetch_update_series_pages(ref_pages)
		self.fetch_update_releases(releases)

		soup = self.wg.getSoup(HOMEPAGE_URL + "/?pg=2")

		ref_pages, releases = self.hpf.extractSeriesReleases(HOMEPAGE_URL + "/?pg=2", soup)
		self.fetch_update_series_pages(ref_pages)
		self.fetch_update_releases(releases)


if __name__ == "__main__":
	logging.basicConfig(level=logging.DEBUG)

	# mon = NuMonitor()
	mon = NuPageUpdater()

	mon.go()





