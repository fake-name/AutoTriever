
import pprint
import random

import salt.cloud
import salt.client
import salt.config


def generate_do_conf():

	provider = "do"
	kwargs = {
		'image': 'ubuntu-14-04-x64',
		'size': '512mb',
		'vm_size': '512mb',
		'private_networking' : False,
		'location' : random.choice(['ams2', 'ams3', 'blr1', 'fra1', 'lon1', 'nyc1', 'nyc2', 'nyc3', 'sfo1', 'sgp1', 'tor1']),


	}
	return provider, kwargs

def instantiate_minion():
	cc = salt.cloud.CloudClient('/etc/salt/cloud')


	# provider, kwargs = generate_do_conf()
	# print("Creating instance...")
	# instance = cc.create(names=['test-1'], provider=provider, **kwargs)

	# # print("Instance: ", instance)
	# with open("minion.txt", "w") as fp:
	# 	fp.write(pprint.pformat(instance))
	# with open("minion_raw.txt", "w") as fp:
	# 	fp.write(str(instance))

	cc.destroy('test-1')
	# images = cc.list_images()
	# locs   = cc.list_locations()
	# sizes  = cc.list_sizes()
	# pprint.pprint(images)
	# pprint.pprint(locs)
	# pprint.pprint(sizes)

def dump_minion_conf():
	conf = salt.config.client_config('/etc/salt/minion')
	print(conf)

if __name__ == '__main__':
	instantiate_minion()
	# dump_minion_conf()
