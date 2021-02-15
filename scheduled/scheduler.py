

import logging
import apscheduler.events
from apscheduler.schedulers.background import BackgroundScheduler
from . import jobs


log = logging.getLogger("Main.Runtime")


def run_job(job_instance):
	log.info("Scheduler executing class: %s", job_instance)
	instance = job_instance()
	instance.go()


def schedule_jobs(sched):

	# start = datetime.datetime.now() + datetime.timedelta(minutes=1)
	for module, name, interval_seconds in jobs.JOBS:
		log.info("Scheduling %s to run every %s hours.", module, interval_seconds / (60 * 60))
		sched.add_job(run_job,
				trigger            = 'interval',
				seconds            = interval_seconds,
				start_date         = '2000-1-1 0:00:00',
				name               = name,
				id                 = name,
				args               = (module,),
				coalesce           = True,
				max_instances      = 1,
				misfire_grace_time = 60 * 60 * 2,
			)



JOB_MAP = {
		apscheduler.events.EVENT_SCHEDULER_STARTED  : "EVENT_SCHEDULER_STARTED",
		apscheduler.events.EVENT_SCHEDULER_SHUTDOWN : "EVENT_SCHEDULER_SHUTDOWN",
		apscheduler.events.EVENT_SCHEDULER_PAUSED   : "EVENT_SCHEDULER_PAUSED",
		apscheduler.events.EVENT_SCHEDULER_RESUMED  : "EVENT_SCHEDULER_RESUMED",
		apscheduler.events.EVENT_EXECUTOR_ADDED     : "EVENT_EXECUTOR_ADDED",
		apscheduler.events.EVENT_EXECUTOR_REMOVED   : "EVENT_EXECUTOR_REMOVED",
		apscheduler.events.EVENT_JOBSTORE_ADDED     : "EVENT_JOBSTORE_ADDED",
		apscheduler.events.EVENT_JOBSTORE_REMOVED   : "EVENT_JOBSTORE_REMOVED",
		apscheduler.events.EVENT_ALL_JOBS_REMOVED   : "EVENT_ALL_JOBS_REMOVED",
		apscheduler.events.EVENT_JOB_ADDED          : "EVENT_JOB_ADDED",
		apscheduler.events.EVENT_JOB_REMOVED        : "EVENT_JOB_REMOVED",
		apscheduler.events.EVENT_JOB_MODIFIED       : "EVENT_JOB_MODIFIED",
		apscheduler.events.EVENT_JOB_SUBMITTED      : "EVENT_JOB_SUBMITTED",
		apscheduler.events.EVENT_JOB_MAX_INSTANCES  : "EVENT_JOB_MAX_INSTANCES",
		apscheduler.events.EVENT_JOB_EXECUTED       : "EVENT_JOB_EXECUTED",
		apscheduler.events.EVENT_JOB_ERROR          : "EVENT_JOB_ERROR",
		apscheduler.events.EVENT_JOB_MISSED         : "EVENT_JOB_MISSED",
		apscheduler.events.EVENT_ALL                : "EVENT_ALL",
	}


def job_evt_listener(event):
	if hasattr(event, "exception") and event.exception:
		log.info('Job crashed: %s', event.job_id)
		log.info('Traceback: %s', event.traceback)
	else:
		log.info('Job event code: %s, job: %s', JOB_MAP[event.code], event.job_id)

	if event.code == apscheduler.events.EVENT_JOB_MAX_INSTANCES:
		log.error("Missed job execution! Killing job executor to unstick jobs")

		import ctypes
		ctypes.string_at(1)
		import os
		os.kill(0,4)

def run_scheduler_thread():
	log.info("Setting up scheduler.")
	aplogger = logging.getLogger('apscheduler')
	if aplogger.hasHandlers():
		aplogger.handlers.clear()

	aplogger.setLevel(logging.ERROR)

	sched = BackgroundScheduler({
			'apscheduler.jobstores.default': {
				'type': 'memory'
			},
			'apscheduler.executors.default': {
				'class': 'apscheduler.executors.pool:ThreadPoolExecutor',
				'max_workers'                              : 5
			},
			'apscheduler.job_defaults.coalesce'            : True,
			'apscheduler.job_defaults.max_instances'       : 1,
			'apscheduler.job_defaults.misfire_grace_time ' : 60 * 60 * 2,
		})

	sched.start()

	sched.add_listener(job_evt_listener,
			apscheduler.events.EVENT_JOB_EXECUTED |
			apscheduler.events.EVENT_JOB_ERROR    |
			apscheduler.events.EVENT_JOB_MISSED   |
			apscheduler.events.EVENT_JOB_MAX_INSTANCES
		)

	schedule_jobs(sched)
	aplogger.setLevel(logging.DEBUG)
	log.info("Scheduler is running!")

