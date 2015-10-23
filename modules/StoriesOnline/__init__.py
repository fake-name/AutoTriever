

import modules.StoriesOnline.Scrape

class StoriesOnlineFetch_WebRequest(modules.StoriesOnline.Scrape.StoriesOnlineFetch):

	name = 'StoriesOnlineFetch'

	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)

		self.calls = {
			'getpage'               : self.getpage,
			'getFileAndName'        : self.getFileAndName
		}

