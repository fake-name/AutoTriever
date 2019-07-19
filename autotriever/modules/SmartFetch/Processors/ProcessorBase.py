
import logging
import abc
import WebRequest

class ProcessorBase(object, metaclass=abc.ABCMeta):

	@abc.abstractproperty
	def log_name(self):
		pass

	def __init__(self, wg:WebRequest.WebGetRobust):
		self.log = logging.getLogger(self.log_name)
		self.wg  = wg


	def preprocess_content(self, url:str, lowerspliturl:tuple, mimetype:str, contentstr:[str,bytes]):
		raise RuntimeError("Cannot call preprocess_content that is not overridden!")

	@staticmethod
	@abc.abstractmethod
	def wants_url(lowerspliturl:tuple, mimetype:str):
		raise RuntimeError("Cannot call wants_url that is not overridden!")


	# Proxy calls for enforcing call-correctness
	@classmethod
	def preprocess(cls, url:str, lowerspliturl:tuple, mimeType:str, content:[str,bytes], wg:WebRequest.WebGetRobust):
		instance = cls(wg)
		instance.log.info("Preprocessing content from URL: '%s'", url)
		return instance.preprocess_content(url, lowerspliturl, mimeType, content)
