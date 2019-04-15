

from modules.PreprocessFetch import QidianTools
from modules.PreprocessFetch import LndbTools
from modules.PreprocessFetch import SmartDispatcher


class PluginInterface_PreprocessFetch(object):

	name = 'PreprocessFetch'

	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)


		self.calls = {
			'qidianSmartFeedFetch'                  : self.qidianSmartFeedFetch,
			'qidianProcessReleaseList'              : self.qidianProcessReleaseList,

			'lndbRenderFetch'                       : self.lndbRenderFetch,

			'smartGetItem'                          : self.smartGetItem,
		}


	def qidianSmartFeedFetch(self, feed_url, meta):

		proc = QidianTools.QidianProcessor()
		content = proc.qidianProcessFeedUrls(feed_url, meta)

		return content, '', 'application/rss+xml'

	def qidianProcessReleaseList(self, feed_urls):

		proc = QidianTools.QidianProcessor()
		content = proc.process_release_list(feed_urls)

		return content

	def lndbRenderFetch(self, *args, **kwargs):
		proc = LndbTools.LndbProcessor()
		ret = proc.forward_render_fetch(*args, **kwargs)
		return ret

	def smartGetItem(self, *args, **kwargs):
		proc = SmartDispatcher.SmartDispatcher()
		ret = proc.smartGetItem(*args, **kwargs)
		return ret

	# def test(self):
	# 	print("Exec()ing `runTest.sh` from directory root!")

	# 	import subprocess
	# 	command = "./runTests.sh"

	# 	process = subprocess.Popen(command.split(), stdout=subprocess.PIPE)
	# 	output, error = process.communicate()

	# 	print("Command output: ", output)
	# 	print("Command errors: ", error)
