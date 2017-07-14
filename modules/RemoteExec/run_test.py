
import logging
import msgpack
import multiprocessing


def client_thread(mqueue):

	from modules.RemoteExec import serialize
	from modules.RemoteExec import test_cls

	def get_serialized():
		return serialize.serialize_class(test_cls.TestClass)

	ser_obj_in = get_serialized()

	message_bytes = msgpack.packb(ser_obj_in, use_bin_type=True)
	# print(message_bytes)

	mqueue.put(message_bytes)

def run_test(self):
	print("Starting process")
	mqueue = multiprocessing.Queue()
	proc = multiprocessing.Process(target=client_thread, args=(mqueue, ))
	proc.start()
	proc.join()
	print("Process generated class")

	message_bytes = mqueue.get()
	print("Retrieved bytes:", len(message_bytes))

	# message_bytes = b'\x84\xa7callcls\xc4,\x80\x03cmodules.RemoteExec.test_cls\nTestClass\nq\x00.\xa8callname\xa9TestClass\xabexec_method\xa2go\xa6source\xda\x01\x1fclass '
	# 'TestClass(object):\n\tdef __init__(self, wg=None):\n\t\tself.log = logging.getLogger("Main.RemoteExec.Tester")\n\t\tself.wg = wg\n\t\tself.log.info("TestClass Instant'
	# 'iated")\n\n\tdef go(self):\n\t\tself.log.info("TestClass go() called")\n\t\tself.log.info("WG: %s", self.wg)\n\n\t\treturn "Test sez wut?"\n'

	ser_obj_out = msgpack.unpackb(message_bytes, use_list=True, encoding='utf-8')

	ret = self.call_code(ser_obj_out)

	self.log.info("Return size: %s", len(ret))

	return ret