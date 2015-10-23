
import logging


class StoriesOnlineFetch(object):

	def __init__(self):
		print("StoriesOnlineFetch __init__()")
		self.log = logging.getLogger("Main.Text.StoriesOnline")
		super().__init__()
		self.wg = webFunctions.WebGetRobust()

		self.initializeStartUrls()

	def getpage(self, *args, **kwargs):
		return self.wg.getpage(*args, **kwargs)

	def getFileAndName(self, *args, **kwargs):
		return self.wg.getpage(*args, **kwargs)

