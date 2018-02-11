
class VmCreateFailed(Exception):
	pass

class LocationNotAvailableResponse(VmCreateFailed):
	pass
class InvalidDeployResponse(VmCreateFailed):
	pass
class InvalidExpectParameter(VmCreateFailed):
	pass