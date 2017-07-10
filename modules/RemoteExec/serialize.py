
import dill
import logging

def serialize_class(tgt_class, exec_method='go'):
	ret = {
		'source'      : dill.source.getsource(tgt_class),
		'callname'    : tgt_class.__name__,
		'callcls'     : dill.dumps(tgt_class),
		'exec_method' : exec_method,
	}
	return ret

def deserialize_class(class_blob):
	assert 'source'      in class_blob
	assert 'callcls'     in class_blob
	assert 'exec_method' in class_blob

	code = compile(class_blob['source'], "no filename", "exec")
	exec(code)
	# This call relies on the source that was exec()ed having defined the class
	# that will now be unserialized.
	cls_def = dill.loads(class_blob['callcls'])
	print("cls_def:", cls_def)
	return cls_def, class_blob['exec_method']

