
import logging
import msgpack

from autotriever.modules.RemoteExec import serialize
from autotriever.modules.RemoteExec import run_test
import WebRequest


class PluginInterface_RemoteExec(object):

	name = 'RemoteExec'
	can_send_partials = True

	def __init__(self, settings=None, *args, **kwargs):
		super().__init__()
		self.log = logging.getLogger("Main.RemoteExec.Caller")

		self.settings = settings if settings else {}
		twocaptcha_api = self.settings.get('captcha_solvers', {}).get('2captcha', {}).get('api_key', None)
		anticaptcha_api = self.settings.get('captcha_solvers', {}).get('anti-captcha', {}).get('api_key', None)


		self.wg = WebRequest.WebGetRobust(
				twocaptcha_api_key  = twocaptcha_api,
				anticaptcha_api_key = anticaptcha_api,
			)


		self.calls = {
			'callCode'               : self.call_code,
		}

	def call_code(self, code_struct, extra_env=None, *call_args, **call_kwargs):
		self.log.info("RPC Call for %s byte class!" , len(code_struct['source']))
		class_def, call_name = serialize.deserialize_class(code_struct)

		call_env = {
			'wg'     : self.wg,
		}

		if extra_env:
			for key, value in extra_env.items():
				extra_env[key] = value

		instantiated = class_def(**call_env)
		self.log.info("Instantiated instance of %s. Calling member function %s.", class_def, call_name)
		self.log.info("Call args: '%s', kwargs: '%s'.", call_args, call_kwargs)

		return getattr(instantiated, call_name)(*call_args, **call_kwargs)

	def test(self):
		run_test.validate_deserialize(self)
