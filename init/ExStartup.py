
import modules.WebRequest
import json
import copy
import logging
import os.path

import main

import modules.ExContentLoader
class ExInit(modules.ExContentLoader.ExContentLoader):



	def __init__(self):
		self.wg = modules.WebRequest.WebGetRobust(logPath="Main.SadPanda.Web")
		self.log = logging.getLogger('Main.SadPanda.Interface')

		self.settings = main.loadSettings()



	def doSetup(self):
		self.checkLogin()


class InitSystem_ExScraper(ExInit):

	name = 'WebRequest'

	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)

		self.calls = {
			'init'               : self.doSetup
		}
