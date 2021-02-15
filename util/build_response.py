
'''
Example response (json):


{
	"ret": [
			"<!DOCTYPE html>\n<html class <snip> .....",              # File contents
			"power-of-the-samsara_46680530493695012",                 # File name
			"text/html"                                               # File Mimetype
		],
	"success": true,                                                  # Indicates whether the call hit an exception
	"cancontinue": true,                                              # Used in remote agent for internal purposes. Does not need to be
	                                                                  # fed back to the client, really
	"dispatch_key": "fetcher",                                        # Command sent to AutoTriever Instance. Simply fed back from job
	                                                                  # Unchecked

	"module": "SmartWebRequest",                                      # Command sent to AutoTriever Instance. Simply fed back from job
	                                                                  # Checked
	"call": "smartGetItem",                                           # Command sent to AutoTriever Instance. Simply fed back from job
	                                                                  # Checked

	"user": "scrape-worker-1",                                        # Inserted by the remote client. Specifies which of the worker pool completed the job
	"user_uuid": "urn:uuid:44699d1f-3ba3-4823-83de-b3cd00b3cd07",     # Inserted by the remote client. Should be unique on a per-worker basis.

	"partial": false,                                                 # Set to indicate the job in question isn't complete, so it's jobid shouldn't
	                                                                  # be removed from the active jobs pool.

	"jobid": 10361539052,                                             # Job ID. Generally a database PK.
	"jobmeta": {
		"sort_key": "77acf9f66f5611ebb7ded69d0ffee0f7",               # Sort key used for demultiplexing. Used to link a job with the appropriate
	                                                                  # RX Queue so it get's returned to the bucket it came from.
	                                                                  # Either `sort_key` or `qname` must be present to place the job
	                                                                  # response into the correct local queue.

		"started_at": 1613370274.1073031                              # Linux timestamp when the job was started. Used for stats tracking
		"qname": "ProcessedMirror",                                   # Override the response queue name in the RPC Dipatcher system.
	},

	"extradat": {                                                     # Extradat ['dispatch_mode', 'netloc'] are used for
		"mode": "fetch",                                              # feeding back into the rate-limiting system without
		"netloc": "www.webnovel.com",                                 # needing to reach into the database to get the job netloc.
		"dispatch_mode": "random"                                     # There is no error if they are missing.
	}
}


'''


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

