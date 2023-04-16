
import json
import os

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


	return settings

SETTINGS = loadSettings()


SQLALCHEMY_DATABASE_URI = SETTINGS.get("sqlalchemy_db_uri", None)

if SQLALCHEMY_DATABASE_URI is None:
	SQLALCHEMY_DATABASE_URI = 'sqlite:///db_sqlite.db'

