

import json
import ssl
import os.path
import os

from .deps import logSetup




class SettingsLoadFailed(ValueError):
	pass

def loadSettings():

	settings = None

	sPaths = ['./settings.json', '../settings.json']

	for sPath in sPaths:
		if not os.path.exists(sPath):
			continue
		with open('./settings.json', 'r') as fp:
			print("Found settings.json file! Loading settings.")
			settings = json.load(fp)

	if not settings and 'SCRAPE_CREDS' in os.environ:
		print("Found 'SCRAPE_CREDS' environment variable! Loading settings.")
		settings = json.loads(os.environ['SCRAPE_CREDS'])

	if not settings:
		raise SettingsLoadFailed("No settings.json file or 'SCRAPE_CREDS' environment variable found!")

	return settings


def findCert():
	'''
	Verify the SSL cert exists in the proper place.
	'''

	curFile = os.path.abspath(__file__)

	curDir = os.path.split(curFile)[0]
	caCert = os.path.abspath(os.path.join(curDir, './certs/cacert.pem'))
	cert = os.path.abspath(os.path.join(curDir, './certs/cert.pem'))
	keyf = os.path.abspath(os.path.join(curDir, './certs/key.pem'))

	assert os.path.exists(caCert), "No certificates found on path '%s'" % caCert
	assert os.path.exists(cert), "No certificates found on path '%s'" % cert
	assert os.path.exists(keyf), "No certificates found on path '%s'" % keyf

	return {
					"cert_reqs": ssl.CERT_REQUIRED,
					"ca_certs": caCert,
					"keyfile": keyf,
					"certfile": cert,
	}

