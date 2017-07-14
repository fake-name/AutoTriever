
import logging


class TestClass(object):
	def __init__(self, wg=None):
		self.log = logging.getLogger("Main.RemoteExec.Tester")
		self.wg = wg
		self.log.info("TestClass Instantiated")

	def go(self):
		self.log.info("TestClass go() called")
		self.log.info("WG: %s", self.wg)

		return "Test sez wut?"

