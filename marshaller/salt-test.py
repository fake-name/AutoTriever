
import salt.cloud
import logSetup

def testf():

	logSetup.initLogging()
	print("Doing testing!")

	cc = salt.cloud.CloudClient('/etc/salt/cloud')
	cc.create(names        = ['test-1'],
		provider           ='vultr',
		private_networking = False,
		image              = 'Ubuntu 16.04 x64',
		location           = 40,
		size               = u'29',
		script             = "bootstrap-salt-delay",
		script_args        = "-D",
		)

if __name__ == '__main__':

	testf()



