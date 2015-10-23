
import modules.WebRequest.WebRequest

class PluginInterface_WebRequest(modules.WebRequest.WebRequest.WebGetRobust):

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

