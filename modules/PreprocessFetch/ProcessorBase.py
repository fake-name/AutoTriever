
import abc
import logging
import re
import time
import datetime
import json
import feedparser
from feedgen.feed import FeedGenerator
from util.WebRequest import WebGetRobust
from util.WebRequest import Exceptions as WgExceptions

class ProcessorBase(object, metaclass=abc.ABCMeta):

	@abc.abstractproperty
	def log(self):
		pass

	@abc.abstractmethod
	def __init__(self):
		pass

