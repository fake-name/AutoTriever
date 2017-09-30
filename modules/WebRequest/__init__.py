
from util.WebRequest import WebGetRobust

class PluginInterface_WebRequest(WebGetRobust):

	name = 'WebRequest'

	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)

		self.calls = {
			'getpage'                  : self.getpage,
			'getItem'                  : self.getItem,
			'getHead'                  : self.getHead,
			'getFileAndName'           : self.getFileAndName,
			'addCookie'                : self.addCookie,
			'addSeleniumCookie'        : self.addSeleniumCookie,
			'stepThroughCloudFlare'    : self.stepThroughCloudFlare,

			'chromiumGetRenderedItem'  : self.chromiumGetRenderedItem,
			'getHeadChromium'          : self.getHeadChromium,
			'getHeadTitleChromium'     : self.getHeadTitleChromium,
			'getItemChromium'          : self.getItemChromium,
		}

	def test(self):
		print("Exec()ing `runTest.sh` from directory root!")

		import subprocess
		command = "./runTests.sh"

		process = subprocess.Popen(command.split(), stdout=subprocess.PIPE)
		output, error = process.communicate()

		print("Command output: ", output)
		print("Command errors: ", error)
