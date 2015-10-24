

from modules.StoriesOnline.Scrape import StoriesOnlineFetch

class PluginInterface_StoriesOnlineFetch(StoriesOnlineFetch):

	name = 'StoriesOnlineFetch'

	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)

		self.calls = {
			'getpage'               : self.getpage,
			'getFileAndName'        : self.getFileAndName
		}

