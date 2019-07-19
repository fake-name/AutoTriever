
import logging
import abc
import WebRequest

class PreemptProcessorBase(object, metaclass=abc.ABCMeta):

	@abc.abstractproperty
	def log_name(self):
		pass

	def __init__(self, wg:WebRequest.WebGetRobust):
		self.log = logging.getLogger(self.log_name)
		self.wg  = wg


	@abc.abstractmethod
	def premptive_handle_content(self, url:str):
		raise RuntimeError("Cannot call premptive_handle_content that is not overridden!")


	@staticmethod
	@abc.abstractmethod
	def preemptive_wants_url(lowerspliturl:tuple):
		raise RuntimeError("Cannot call preemptive_wants_url that is not overridden!")


	@classmethod
	def premptive_handle(cls, url:str, wg:WebRequest.WebGetRobust):
		instance = cls(wg)
		return instance.premptive_handle_content(url)


