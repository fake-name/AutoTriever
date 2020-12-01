

def bundle_func_resp(
			ret,
			dispatch_key,
			module,
			call,
			success     = True,
			cancontinue = True
		):

	response = {
		'ret'          : ret,
		'success'      : success,
		'cancontinue'  : cancontinue,
		'dispatch_key' : dispatch_key,
		'module'       : module,
		'call'         : call,
	}

	return response

