
from util.WebRequest import WebGetRobust

class PluginInterface_WebRequest(WebGetRobust):

	name = 'WebRequest'

	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)

		self.calls = {
			'getpage'               : self.getpage,
			'getFileAndName'        : self.getFileAndName,
			'addCookie'             : self.addCookie,
			'addSeleniumCookie'     : self.addSeleniumCookie,
			'stepThroughCloudFlare' : self.stepThroughCloudFlare,
		}

