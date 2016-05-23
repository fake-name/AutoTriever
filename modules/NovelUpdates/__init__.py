
from util.WebRequest import WebGetRobust
import urllib.error

class PluginInterface_NovelUpdates(WebGetRobust):

	name = 'NUWebRequest'

	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)

		self.calls = {
			'getpage'               : self.getpage,
			'getItem'               : self.getItem_Wrapper,
			'getHead'               : self.getHead_Wrapper,
			'getFileAndName'        : self.getFileAndName,
			'addCookie'             : self.addCookie,
			'addSeleniumCookie'     : self.addSeleniumCookie,
			'stepThroughCloudFlare' : self.stepThroughCloudFlare,
		}

	def getItem_Wrapper(self, url, *args, **kwargs):
		try:
			return self.getItem(url, *args, **kwargs)
		except urllib.error.HTTPError:
			self.stepThroughCloudFlare(url, titleContains = 'Novel Updates')
			return self.getItem(url, *args, **kwargs)

	def getHead_Wrapper(self, url, *args, **kwargs):
		try:
			return self.getHead(url, *args, **kwargs)
		except urllib.error.HTTPError:
			self.stepThroughCloudFlare(url, titleContains = 'Novel Updates')
			return self.getHead(url, *args, **kwargs)

