#!/usr/bin/env python3
import client


class RpcCallDispatcher(client.RpcHandler):
	'''
	dispatch calls.

	Call dispatch is done dynamically, by looking up class attributes.

	Callable functions must be named `call_{functionmame}`


	'''




	def process(self, command):
		if not 'taskname' in command:

			ret = {
				'success'     : False,
				'error'       : "No taskname in message!",
				'cancontinue' : True
			}
			return ret

		callFunc = getattr(self, 'call_{name}'.format(name=command['taskname']), False)
		if not callFunc:
			# TODO: Add NAKing here. Will require changes to AmqpConnector.
			ret = {
				'success'     : False,
				'error'       : "Function not present on client!",
				'cancontinue' : True
			}
			return ret


		args = []
		kwargs = {}
		if 'args' in command:
			args = command['args']
		if 'kwargs' in command:
			kwargs = command['kwargs']

		ret = callFunc(*args, **kwargs)

		response = {
			'ret' : ret,
			'success' : True
		}


		return response
