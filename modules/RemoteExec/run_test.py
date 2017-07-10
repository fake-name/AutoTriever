
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
	print(message_bytes)

	mqueue.put(message_bytes)

def run_test(self):
	print("Starting process")
	mqueue = multiprocessing.Queue()
	proc = multiprocessing.Process(target=client_thread, args=(mqueue, ))
	proc.start()
	proc.join()
	print("Process generated class")

	message_bytes = mqueue.get_nowait()
	print("Retrieved bytes:", message_bytes)


	ser_obj_out = msgpack.unpackb(message_bytes, use_list=True, encoding='utf-8')

	ret = self.call_code(ser_obj_out)

	self.log.info("Return size: %s", len(ret))

	return ret