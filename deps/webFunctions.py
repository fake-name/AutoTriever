#!/usr/bin/python3
import sys
import codecs

import urllib.request, urllib.parse, urllib.error
import os.path

import time
import http.cookiejar

import traceback

import logging
import zlib
import bs4
import deps.userAgents
import re
import gzip
import io



import selenium.webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities



#pylint: disable-msg=E1101, C0325, R0201, W0702, W0703

# A urllib2 wrapper that provides error handling and logging, as well as cookie management. It's a bit crude, but it works.
# Also supports transport compresion.
# OOOOLLLLLLDDDDD, has lots of creaky internals. Needs some cleanup desperately, but lots of crap depends on almost everything.
# Arrrgh.

from threading import Lock
cookieWriteLock = Lock()


class WebGetRobust:
	COOKIEFILE = 'cookies.lwp'				# the path and filename to save your cookies in
	cj = None
	cookielib = None
	opener = None

	errorOutCount = 2
	retryDelay = 1.5


	data = None

	# if test=true, no resources are actually fetched (for testing)
	# creds is a list of 3-tuples that gets inserted into the password manager.
	# it is structured [(top_level_url1, username1, password1), (top_level_url2, username2, password2)]
	def __init__(self, test=False, creds=None, logPath="Main.Web"):
		self.log = logging.getLogger(logPath)
		print("Webget init! Logpath = ", logPath)
		if creds:
			print("Have creds for a domain")
		if test:
			self.log.warning("-----------------------------------------------------------------------------------------------")
			self.log.warning("WARNING: WebGet in testing mode!")
			self.log.warning("-----------------------------------------------------------------------------------------------")

		# Due to general internet people douchebaggyness, I've basically said to hell with it and decided to spoof a whole assortment of browsers
		# It should keep people from blocking this scraper *too* easily
		self.browserHeaders = deps.userAgents.getUserAgent()

		self.testMode = test		# if we don't want to actually contact the remote server, you pass a string containing
									# pagecontent for testing purposes as test. It will get returned for any calls of getpage()

		self.data = urllib.parse.urlencode(self.browserHeaders)


		if creds:
			print("Have credentials, installing password manager into urllib handler.")
			passManager = urllib.request.HTTPPasswordMgrWithDefaultRealm()
			for url, username, password in creds:
				passManager.add_password(None, url, username, password)
			self.credHandler = urllib.request.HTTPBasicAuthHandler(passManager)
		else:
			self.credHandler = None

		self.loadCookies()

	def loadCookies(self):

		self.cj = http.cookiejar.LWPCookieJar()		# This is a subclass of FileCookieJar
												# that has useful load and save methods
		if self.cj is not None:
			if os.path.isfile(self.COOKIEFILE):
				try:
					self.cj.load(self.COOKIEFILE)
					self.log.info("Loading CookieJar")
				except:
					self.log.critical("Cookie file is corrupt/damaged?")

			if http.cookiejar is not None:
				self.log.info("Installing CookieJar")
				self.log.debug(self.cj)
				cookieHandler = urllib.request.HTTPCookieProcessor(self.cj)
				if self.credHandler:
					print("Have cred handler. Building opener using it")
					self.opener = urllib.request.build_opener(cookieHandler, self.credHandler)
				else:
					print("No cred handler")
					self.opener = urllib.request.build_opener(cookieHandler)
				#self.opener.addheaders = [('User-Agent', 'Mozilla/4.0 (compatible; MSIE 5.5; Windows NT)')]
				self.opener.addheaders = self.browserHeaders
				#urllib2.install_opener(self.opener)

		for cookie in self.cj:
			self.log.debug(cookie)
			#print cookie


	def chunkReport(self, bytesSoFar, totalSize):
		if totalSize:
			percent = float(bytesSoFar) / totalSize
			percent = round(percent * 100, 2)
			self.log.info("Downloaded %d of %d bytes (%0.2f%%)" % (bytesSoFar, totalSize, percent))
		else:
			self.log.info("Downloaded %d bytes" % (bytesSoFar))


	def chunkRead(self, response, chunkSize=2 ** 18, reportHook=None):
		contentLengthHeader = response.info().getheader('Content-Length')
		if contentLengthHeader:
			totalSize = contentLengthHeader.strip()
			totalSize = int(totalSize)
		else:
			totalSize = None
		bytesSoFar = 0
		pgContent = ""
		while 1:
			chunk = response.read(chunkSize)
			pgContent += chunk
			bytesSoFar += len(chunk)

			if not chunk:
				break

			if reportHook:
				reportHook(bytesSoFar, chunkSize, totalSize)

		return pgContent



	def getSoup(self, *args, **kwargs):
		if 'returnMultiple' in kwargs and kwargs['returnMultiple']:
			raise ValueError("getSoup cannot be called with 'returnMultiple' being true")

		if 'soup' in kwargs and kwargs['soup']:
			raise ValueError("getSoup contradicts the 'soup' directive!")

		page = self.getpage(*args, **kwargs)
		if isinstance(page, bytes):
			raise ValueError("Received content not decoded! Cannot parse!")

		soup = bs4.BeautifulSoup(page)
		return soup


	def getFileAndName(self, *args, **kwargs):
		if 'returnMultiple' in kwargs:
			raise ValueError("getFileAndName cannot be called with 'returnMultiple'")

		if 'soup' in kwargs and kwargs['soup']:
			raise ValueError("getFileAndName contradicts the 'soup' directive!")

		kwargs["returnMultiple"] = True

		pgctnt, pghandle = self.getpage(*args, **kwargs)

		info = pghandle.info()
		if not 'Content-Disposition' in info:
			hName = ''
		elif not 'filename=' in info['Content-Disposition']:
			hName = ''
		else:
			hName = info['Content-Disposition'].split('filename=')[1]


		return pgctnt, hName


	def buildRequest(self, pgreq, postData, addlHeaders, binaryForm):
		# Encode Unicode URL's properly
		pgreq = iri2uri(pgreq)

		try:
			params = {}
			headers = {}
			if postData != None:
				self.log.info("Making a post-request!")
				params['data'] = urllib.parse.urlencode(postData).encode("utf-8")
			if addlHeaders != None:
				self.log.info("Have additional GET parameters!")
				headers = addlHeaders
			if binaryForm:
				self.log.info("Binary form submission!")
				if 'data' in params:
					raise ValueError("You cannot make a binary form post and a plain post request at the same time!")

				params['data']            = binaryForm.make_result()
				headers['Content-type']   =  binaryForm.get_content_type()
				headers['Content-length'] =  len(params['data'])


			return urllib.request.Request(pgreq, headers=headers, **params)

		except:
			self.log.critical("Invalid header or url")
			raise


	def decodeHtml(self, pageContent, cType):

		if (";" in cType) and ("=" in cType): 		# the server is reporting an encoding. Now we use it to decode the

			# Some wierdos put two charsets in their headers:
			# `text/html;Charset=UTF-8;charset=UTF-8`
			# Split, and take the first two entries.
			dummy_docType, charset = cType.split(";")[:2]
			charset = charset.split("=")[-1]


		else:		# The server is not reporting an encoding in the headers.

			# this *should* probably be done using a parser.
			# However, it seems to be grossly overkill to shove the whole page (which can be quite large) through a parser just to pull out a tag that
			# should be right near the page beginning anyways.
			# As such, it's a regular expression for the moment

			# Regex is of bytes type, since we can't convert a string to unicode until we know the encoding the
			# bytes string is using, and we need the regex to get that encoding
			coding = re.search(rb"charset=[\'\"]?([a-zA-Z0-9\-]*)[\'\"]?", pageContent, flags=re.IGNORECASE)

			cType = b""
			charset = None
			try:
				if coding:
					cType = coding.group(1)
					codecs.lookup(cType.decode("ascii"))
					charset = cType.decode("ascii")

			except LookupError:

				# I'm actually not sure what I was thinking when I wrote this if statement. I don't think it'll ever trigger.
				if (b";" in cType) and (b"=" in cType): 		# the server is reporting an encoding. Now we use it to decode the

					dummy_docType, charset = cType.split(b";")
					charset = charset.split(b"=")[-1]

			if not charset:
				self.log.warning("Could not find encoding information on page - Using default charset. Shit may break!")
				charset = "iso-8859-1"

		try:
			pageContent = str(pageContent, charset)

		except UnicodeDecodeError:
			self.log.error("Encoding Error! Stripping invalid chars.")
			pageContent = pageContent.decode('utf-8', errors='ignore')

		return pageContent

	def decompressContent(self, coding, pgctnt):
		#preLen = len(pgctnt)
		if coding == 'deflate':
			compType = "deflate"

			pgctnt = zlib.decompress(pgctnt, -zlib.MAX_WBITS)

		elif coding == 'gzip':
			compType = "gzip"

			buf = io.BytesIO(pgctnt)
			f = gzip.GzipFile(fileobj=buf)
			pgctnt = f.read()

		elif coding == "sdch":
			raise ValueError("Wait, someone other then google actually supports SDCH compression?")

		else:
			compType = "none"

		return compType, pgctnt



	def getItem(self, itemUrl):

		try:
			content, handle = self.getpage(itemUrl, returnMultiple=True)
		except:
			print("Failure?")
			if self.rules['cloudflare']:
				if not self.stepThroughCloudFlare(itemUrl, titleNotContains='Just a moment...'):
					raise ValueError("Could not step through cloudflare!")
				# Cloudflare cookie set, retrieve again
				content, handle = self.getpage(itemUrl, returnMultiple=True)
			else:
				raise

		if not content or not handle:
			raise DownloadException("Failed to retreive file from page '%s'!" % itemUrl)

		fileN = urllib.parse.unquote(urllib.parse.urlparse(handle.geturl())[2].split("/")[-1])
		fileN = bs4.UnicodeDammit(fileN).unicode_markup
		mType = handle.info()['Content-Type']

		# If there is an encoding in the content-type (or any other info), strip it out.
		# We don't care about the encoding, since WebFunctions will already have handled that,
		# and returned a decoded unicode object.
		if mType and ";" in mType:
			mType = mType.split(";")[0].strip()

		# *sigh*. So minus.com is fucking up their http headers, and apparently urlencoding the
		# mime type, because apparently they're shit at things.
		# Anyways, fix that.
		if '%2F' in  mType:
			mType = mType.replace('%2F', '/')

		self.log.info("Retreived file of type '%s', name of '%s' with a size of %0.3f K", mType, fileN, len(content)/1000.0)
		return content, fileN, mType


	def decodeTextContent(self, pgctnt, cType):

		if cType:
			if "text/html" in cType or \
				'text/javascript' in cType or    \
				'application/atom+xml' in cType:				# If this is a html/text page, we want to decode it using the local encoding

				pgctnt = self.decodeHtml(pgctnt, cType)

			elif "text/plain" in cType or "text/xml" in cType:
				pgctnt = bs4.UnicodeDammit(pgctnt).unicode_markup

			# Assume JSON is utf-8. Probably a bad idea?
			elif "application/json" in cType:
				pgctnt = pgctnt.decode('utf-8')

			elif "text" in cType:
				self.log.critical("Unknown content type!")
				self.log.critical(cType)

		else:
			self.log.critical("No content disposition header!")
			self.log.critical("Cannot guess content type!")

		return pgctnt

	def retreiveContent(self, pgreq, pghandle, callBack):
		try:
			# If we have a progress callback, call it for chunked read.
			# Otherwise, just read in the entire content.
			if callBack:
				pgctnt = self.chunkRead(pghandle, 2 ** 17, reportHook=callBack)
			else:
				pgctnt = pghandle.read()


			if pgctnt == None:
				return False

			self.log.info("URL fully retrieved.")

			preDecompSize = len(pgctnt)/1000.0

			encoded = pghandle.headers.get('Content-Encoding')
			compType, pgctnt = self.decompressContent(encoded, pgctnt)


			decompSize = len(pgctnt)/1000.0
			# self.log.info("Page content type = %s", type(pgctnt))
			cType = pghandle.headers.get("Content-Type")
			if compType == 'none':
				self.log.info("Compression type = %s. Content Size = %0.3fK. File type: %s.", compType, decompSize, cType)
			else:
				self.log.info("Compression type = %s. Content Size compressed = %0.3fK. Decompressed = %0.3fK. File type: %s.", compType, preDecompSize, decompSize, cType)

			pgctnt = self.decodeTextContent(pgctnt, cType)

			return pgctnt

		except:
			print("pghandle = ", pghandle)

			self.log.error(sys.exc_info())
			traceback.print_exc()
			self.log.error("Error Retrieving Page! - Transfer failed. Waiting %s seconds before retrying", self.retryDelay)

			try:
				self.log.critical("Critical Failure to retrieve page! %s at %s", pgreq.get_full_url(), time.ctime(time.time()))
				self.log.critical("Exiting")
			except:
				self.log.critical("And the URL could not be printed due to an encoding error")
			print()
			self.log.error(pghandle)
			time.sleep(self.retryDelay)

		return False


		# HUGE GOD-FUNCTION.
		# OH GOD FIXME.

		# postData expects a dict
		# addlHeaders also expects a dict
	def getpage(self, requestedUrl, **kwargs):

		# pgreq = fixurl(pgreq)

		# addlHeaders = None, returnMultiple = False, callBack=None, postData=None, soup=False, retryQuantity=None, nativeError=False, binaryForm=False

		# If we have 'soup' as a param, just pop it, and call `getSoup()`.
		if 'soup' in kwargs and kwargs['soup']:
			self.log.warn("'soup' kwarg is depreciated. Please use the `getSoup()` call instead.")
			kwargs.pop('soup')

			return self.getSoup(requestedUrl, **kwargs)

		# Decode the kwargs values
		addlHeaders    = kwargs.setdefault("addlHeaders",     None)
		returnMultiple = kwargs.setdefault("returnMultiple",  False)
		callBack       = kwargs.setdefault("callBack",        None)
		postData       = kwargs.setdefault("postData",        None)
		retryQuantity  = kwargs.setdefault("retryQuantity",   None)
		nativeError    = kwargs.setdefault("nativeError",     False)
		binaryForm     = kwargs.setdefault("binaryForm",      False)



		pgctnt = None
		pghandle = None
		retryCount = 0

		pgreq = self.buildRequest(requestedUrl, postData, addlHeaders, binaryForm)

		errored = False
		lastErr = ""


		if not self.testMode:
			while 1:

				retryCount = retryCount + 1

				if (retryQuantity and retryCount > retryQuantity) or (not retryQuantity and retryCount > self.errorOutCount):
					self.log.error("Failed to retrieve Website : %s at %s All Attempts Exhausted", pgreq.get_full_url(), time.ctime(time.time()))
					pgctnt = None
					try:
						self.log.critical("Critical Failure to retrieve page! %s at %s, attempt %s", pgreq.get_full_url(), time.ctime(time.time()), retryCount)
						self.log.critical("Error: %s", lastErr)
						self.log.critical("Exiting")
					except:
						self.log.critical("And the URL could not be printed due to an encoding error")
					break

				#print "execution", retryCount
				try:
					pghandle = self.opener.open(pgreq)					# Get Webpage

				except urllib.error.HTTPError as e:								# Lotta logging
					self.log.warning("Error opening page: %s at %s On Attempt %s.", pgreq.get_full_url(), time.ctime(time.time()), retryCount)
					self.log.warning("Error Code: %s", e)

					#traceback.print_exc()
					lastErr = e
					try:

						self.log.warning("Original URL: %s", requestedUrl)
						errored = True
					except:
						self.log.warning("And the URL could not be printed due to an encoding error")

					if e.code == 404:
						#print "Unrecoverable - Page not found. Breaking"
						self.log.critical("Unrecoverable - Page not found. Breaking")
						break

					time.sleep(self.retryDelay)

				except UnicodeEncodeError:
					self.log.critical("Unrecoverable Unicode issue retreiving page - %s", requestedUrl)
					break

				except Exception:
					errored = True
					#traceback.print_exc()
					lastErr = sys.exc_info()
					self.log.warning("Retreival failed. Traceback:")
					self.log.warning(lastErr)
					self.log.warning(traceback.format_exc())

					self.log.warning("Error Retrieving Page! - Trying again - Waiting 2.5 seconds")

					try:
						self.log.critical("Error on page - %s", requestedUrl)
					except:
						self.log.critical("And the URL could not be printed due to an encoding error")

					time.sleep(self.retryDelay)


					continue

				if pghandle != None:
					self.log.info("Request for URL: %s succeeded at %s On Attempt %s. Recieving...", pgreq.get_full_url(), time.ctime(time.time()), retryCount)
					pgctnt = self.retreiveContent(pgreq, pghandle, callBack)

					# if retreiveContent did not return false, it managed to fetch valid results, so break
					if pgctnt != False:
						break

		if errored and pghandle != None:
			print(("Later attempt succeeded %s" % pgreq.get_full_url()))
			#print len(pgctnt)
		elif errored and pghandle == None:

			if lastErr and nativeError:
				raise lastErr
			raise urllib.error.URLError("Failed to retreive page!")

		if returnMultiple:
			return pgctnt, pghandle
		else:
			return pgctnt

	def syncCookiesFromFile(self):
		self.log.info("Synchronizing cookies with cookieFile.")
		if os.path.isfile(self.COOKIEFILE):
			self.cj.save("cookietemp.lwp")
			self.cj.load(self.COOKIEFILE)
			self.cj.load("cookietemp.lwp")
		# First, load any changed cookies so we don't overwrite them
		# However, we want to persist any cookies that we have that are more recent then the saved cookies, so we temporarily save
		# the cookies in memory to a temp-file, then load the cookiefile, and finally overwrite the loaded cookies with the ones from the
		# temp file

	def updateCookiesFromFile(self):
		if os.path.exists(self.COOKIEFILE):
			self.log.info("Synchronizing cookies with cookieFile.")
			self.cj.load(self.COOKIEFILE)
		# Update cookies from cookiefile

	def addCookie(self, inCookie):
		self.log.info("Updating cookie!")
		self.cj.set_cookie(inCookie)

	def addSeleniumCookie(self, cookieDict):
		'''
		Install a cookie exported from a selenium webdriver into
		the active opener
		'''
		# print cookieDict
		cookie = http.cookiejar.Cookie(
				version=0
				, name=cookieDict['name']
				, value=cookieDict['value']
				, port=None
				, port_specified=False
				, domain=cookieDict['domain']
				, domain_specified=True
				, domain_initial_dot=False
				, path=cookieDict['path']
				, path_specified=False
				, secure=cookieDict['secure']
				, expires=cookieDict['expiry']
				, discard=False
				, comment=None
				, comment_url=None
				, rest={"httponly":"%s" % cookieDict['httponly']}
				, rfc2109=False
			)

		self.cj.set_cookie(cookie)

	def initLogging(self):
		print("WARNING - Webget logging re-initialized?")
		mainLogger = logging.getLogger("Main")			# Main logger
		mainLogger.setLevel(logging.DEBUG)

		ch = logging.StreamHandler(sys.stdout)
		formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
		ch.setFormatter(formatter)
		mainLogger.addHandler(ch)

	def saveCookies(self, halting=False):

		cookieWriteLock.acquire()
		# print("Have %d cookies before saving cookiejar" % len(self.cj))
		try:
			self.log.info("Trying to save cookies!")
			if self.cj is not None:							# If cookies were used

				self.syncCookiesFromFile()

				self.log.info("Have cookies to save")
				for cookie in self.cj:
					# print(cookie)
					# print(cookie.expires)

					if isinstance(cookie.expires, int) and cookie.expires > 30000000000:		# Clamp cookies that expire stupidly far in the future because people are assholes
						cookie.expires = 30000000000

				self.log.info("Calling save function")
				self.cj.save(self.COOKIEFILE)					# save the cookies again


				self.log.info("Cookies Saved")
			else:
				self.log.info("No cookies to save?")
		except Exception as e:
			pass
			# The destructor call order is too incoherent, and shit fails
			# during the teardown with null-references. The error printout is
			# not informative, so just silence it.
			# print("Possible error on exit (or just the destructor): '%s'." % e)
		finally:
			cookieWriteLock.release()

		# print("Have %d cookies after saving cookiejar" % len(self.cj))
		if not halting:
			self.syncCookiesFromFile()
		# print "Have %d cookies after reloading cookiejar" % len(self.cj)

	def __del__(self):
		# print "WGH Destructor called!"
		self.saveCookies(halting=True)





	def stepThroughCloudFlare(self, url, titleContains):
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
		self.log.info("Attempting to access page through cloudflare browser verification.")

		dcap = dict(DesiredCapabilities.PHANTOMJS)
		wgSettings = dict(self.browserHeaders)

		# Install the headers from the WebGet class into phantomjs
		dcap["phantomjs.page.settings.userAgent"] = wgSettings.pop('User-Agent')
		for headerName in wgSettings:
			dcap['phantomjs.page.customHeaders.{header}'.format(header=headerName)] = wgSettings[headerName]

		driver = selenium.webdriver.PhantomJS(desired_capabilities=dcap)
		driver.set_window_size(1024, 768)

		driver.get(url)

		try:
			WebDriverWait(driver, 20).until(EC.title_contains((titleContains)))
			success = True
			self.log.info("Successfully accessed main page!")
		except TimeoutException:
			self.log.error("Could not pass through cloudflare blocking!")
			success = False
		# Add cookies to cookiejar

		for cookie in driver.get_cookies():
			self.addSeleniumCookie(cookie)
			#print cookie[u"value"]

		self.syncCookiesFromFile()

		return success




# Convert an IRI to a URI following the rules in RFC 3987
#
# The characters we need to enocde and escape are defined in the spec:
#
# iprivate =  %xE000-F8FF / %xF0000-FFFFD / %x100000-10FFFD
# ucschar = %xA0-D7FF / %xF900-FDCF / %xFDF0-FFEF
#         / %x10000-1FFFD / %x20000-2FFFD / %x30000-3FFFD
#         / %x40000-4FFFD / %x50000-5FFFD / %x60000-6FFFD
#         / %x70000-7FFFD / %x80000-8FFFD / %x90000-9FFFD
#         / %xA0000-AFFFD / %xB0000-BFFFD / %xC0000-CFFFD
#         / %xD0000-DFFFD / %xE1000-EFFFD

escape_range = [
	(0xA0, 0xD7FF),
	(0xE000, 0xF8FF),
	(0xF900, 0xFDCF),
	(0xFDF0, 0xFFEF),
	(0x10000, 0x1FFFD),
	(0x20000, 0x2FFFD),
	(0x30000, 0x3FFFD),
	(0x40000, 0x4FFFD),
	(0x50000, 0x5FFFD),
	(0x60000, 0x6FFFD),
	(0x70000, 0x7FFFD),
	(0x80000, 0x8FFFD),
	(0x90000, 0x9FFFD),
	(0xA0000, 0xAFFFD),
	(0xB0000, 0xBFFFD),
	(0xC0000, 0xCFFFD),
	(0xD0000, 0xDFFFD),
	(0xE1000, 0xEFFFD),
	(0xF0000, 0xFFFFD),
	(0x100000, 0x10FFFD),
]

def encode(c):
	retval = c
	i = ord(c)
	for low, high in escape_range:
		if i < low:
			break
		if i >= low and i <= high:
			retval = "".join(["%%%2X" % o for o in c.encode('utf-8')])
			break
	return retval


def iri2uri(uri):
	"""Convert an IRI to a URI. Note that IRIs must be
	passed in a unicode strings. That is, do not utf-8 encode
	the IRI before passing it into the function."""
	original = uri
	if isinstance(uri ,str):
		(scheme, authority, path, query, fragment) = urllib.parse.urlsplit(uri)
		authority = authority.encode('idna').decode('utf-8')
		# For each character in 'ucschar' or 'iprivate'
		#  1. encode as utf-8
		#  2. then %-encode each octet of that utf-8
		uri = urllib.parse.urlunsplit((scheme, authority, path, query, fragment))
		uri = "".join([encode(c) for c in uri])

	# urllib.parse.urlunsplit(urllib.parse.urlsplit({something})
	# strips any trailing "?" chars. While this may be legal according to the
	# spec, it breaks some services. Therefore, we patch
	# the "?" back in if it has been removed.
	if original.endswith("?") and not uri.endswith("?"):
		uri = uri+"?"
	return uri


class DummyLog:									# For testing WebGetRobust (mostly)
	logText = ""

	def __init__(self):
		pass

	def __repr__(self):
		return self.logText

	def write(self, string):
		self.logText = "%s\n%s" % (self.logText, string)

	def close(self):
		pass


if __name__ == "__main__":
	import logSetup
	import sys
	logSetup.initLogging()
	print("Oh HAI")
	wg = WebGetRobust()

	if len(sys.argv) == 3:
		getUrl = sys.argv[1]
		fName  = sys.argv[2]
		print(getUrl, fName)

		content = wg.getpage(getUrl)

		try:
			out = content.encode("utf-8")
		except:
			out = content

		with open(fName, 'wb') as fp:
			fp.write(out)



	content, handle = wg.getpage("http://www.lighttpd.net", returnMultiple = True)
	print((handle.headers.get('Content-Encoding')))
	print(len(content))
	content, handle = wg.getpage("http://www.example.org", returnMultiple = True)
	print((handle.headers.get('Content-Encoding')))
	content, handle = wg.getpage("https://www.google.com/images/srpr/logo11w.png", returnMultiple = True)
	print((handle.headers.get('Content-Encoding')))
	content, handle = wg.getpage("http://www.doujin-moe.us/ajax/newest.php", returnMultiple = True)
	print((handle.headers.get('Content-Encoding')))

	print("SoupGet")
	content_1 = wg.getpage("http://www.lighttpd.net", soup = True)

	content_2 = wg.getSoup("http://www.lighttpd.net")
	assert(content_1 == content_2)
