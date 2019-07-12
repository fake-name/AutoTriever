
import abc

class ProcessorBase(object, metaclass=abc.ABCMeta):

	@abc.abstractproperty
	def log(self):
		pass

	@abc.abstractmethod
	def __init__(self):
		pass

