
import json
import time
import datetime

from apscheduler.jobstores.memory      import MemoryJobStore
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.executors.pool        import ThreadPoolExecutor

from . import AmqpInterface
from . import logSetup

from . import NUSeriesUpdateFilter

def load_settings():
	with open("settings.json") as fp:
		filec = fp.read()
	return json.loads(filec)


def go():
	while 1:
		try:
			# from . import database as db
			settings = load_settings()
			db_sess = None
			fetcher = NUSeriesUpdateFilter.NUSeriesUpdateFilter(db_sess, settings)
			print(fetcher.handlePage("http://www.novelupdates.com"))
			return
		except:
			import traceback

			print("ERROR: Failure when running job!")
			traceback.print_exc()
			time.sleep(30)
	# finally:
	# 	db_sess.close()

executors = {
	'main_jobstore': ThreadPoolExecutor(5),
}
job_defaults = {
	'coalesce': True,
	'max_instances': 1,
}

jobstores = {
	'main_jobstore'      : MemoryJobStore()

}

def start_scheduler():

	sched = BackgroundScheduler(jobstores=jobstores, executors=executors, job_defaults=job_defaults)

	startTime = datetime.datetime.now() + datetime.timedelta(seconds=3)

	sched.add_job(go,
				# args               = (callee.__name__, ),
				trigger            = 'interval',
				seconds            = 60*60*1,
				start_date         = startTime,
				id                 = 0,
				max_instances      = 1,
				replace_existing   = True,
				jobstore           = "main_jobstore",
				misfire_grace_time = 2**30)

	sched.start()

# def dump_db():

# 	from . import database as db
# 	settings = load_settings()
# 	amqp = AmqpInterface.RabbitQueueHandler(settings)
# 	print(amqp)

# 	sess = db.session()
# 	rows = sess.query(db.LinkWrappers).all()
# 	for row in rows:
# 		amqp.putRow(row)

if __name__ == '__main__':
	logSetup.initLogging()
	# dump_db()
	start_scheduler()
	while 1:
		time.sleep(1)

