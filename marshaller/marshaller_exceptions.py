
class VmCreateFailed(Exception):
	pass

class InvalidDeployResponse(VmCreateFailed):
	pass
class InvalidExpectParameter(VmCreateFailed):
	pass