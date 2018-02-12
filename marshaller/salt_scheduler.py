
import time
import logging
import datetime
import sys
import traceback
import multiprocessing
import pytz
from apscheduler.schedulers.blocking import BlockingScheduler
import logSetup
import marshaller_exceptions
import stopit
import settings

if "test" in sys.argv:
	import salt_dummy as salt_runner
else:
	import salt_runner


VPS_NAME_FORMAT = "scrape-worker-{number}"

def hrs_to_sec(in_val):
	return int(in_val * 60 * 60)

def poke_statsd():
	interface = salt_runner.VpsHerder()
	interface.list_nodes()

# We explicitly want a non-locked shared value, as
# that way the worker thread terminating can't result in
# a wedged lock
CREATE_WATCHDOG = multiprocessing.Value("i", lock=False)


class VpsScheduler(object):

	def __init__(self):
		self.log = logging.getLogger("Main.VpsScheduler")

		self.interface = salt_runner.VpsHerder()

		self.sched = BlockingScheduler({
				'apscheduler.job_defaults.coalesce': 'true',
				'apscheduler.timezone': 'UTC',
			})

		self.sched.add_job(poke_statsd,         'interval', seconds=60)
		self.sched.add_job(self.ensure_active_workers, 'interval', seconds=60 * 5)
		self.install_destroyer_jobs()


	def create_vm(self, vm_name):
		vm_idx = int(vm_name.split("-")[-1])-1
		provider = "unknown"
		self.log.info("Creating VM named: %s, index: %s", vm_name, vm_idx)
		try:
			# VM Create time is 30 minutes, max
			with stopit.ThreadingTimeout(60 * 30, swallow_exc=False):
				# This is slightly horrible.
				provider, kwargs = self.interface.generate_conf()
				with self.interface.mon_con.timer("VM-Creation-{}".format(provider)):
					self.interface.make_client(vm_name, provider, kwargs)
					self.interface.configure_client(vm_name, vm_idx)
				self.log.info("VM %s created.", vm_name)
				CREATE_WATCHDOG.value += 1
			self.interface.mon_con.incr("vm-create.{provider}.ok".format(provider=provider))
		except stopit.TimeoutException:
			self.log.error("Timeout instantiating VM %s.", vm_name)
			self.interface.mon_con.incr("vm-create.{provider}.fail.timeout".format(provider=provider))
			for line in traceback.format_exc().split("\n"):
				self.log.error(line)
			for _ in range(5):
				self.destroy_vm(vm_name)
				time.sleep(2.5)
		except marshaller_exceptions.LocationNotAvailableResponse:
			self.log.warning("Failure instantiating VM %s.", vm_name)
			self.interface.mon_con.incr("vm-create.{provider}.fail.locationnotavilable".format(provider=provider))
			for line in traceback.format_exc().split("\n"):
				self.log.warning(line)
			for _ in range(5):
				self.destroy_vm(vm_name)
				time.sleep(2.5)
		except marshaller_exceptions.InvalidDeployResponse:
			self.log.warning("Failure instantiating VM %s.", vm_name)
			self.interface.mon_con.incr("vm-create.{provider}.fail.invaliddeployresponse".format(provider=provider))
			for line in traceback.format_exc().split("\n"):
				self.log.warning(line)
			for _ in range(5):
				self.destroy_vm(vm_name)
				time.sleep(2.5)
		except marshaller_exceptions.InvalidExpectParameter:
			self.log.warning("Failure instantiating VM %s.", vm_name)
			self.interface.mon_con.incr("vm-create.{provider}.fail.invalidexpectparameter".format(provider=provider))
			for line in traceback.format_exc().split("\n"):
				self.log.warning(line)
			for _ in range(5):
				self.destroy_vm(vm_name)
				time.sleep(2.5)
		except marshaller_exceptions.VmCreateFailed:
			self.log.warning("Failure instantiating VM %s.", vm_name)
			self.interface.mon_con.incr("vm-create.{provider}.fail.vmcreatefailed".format(provider=provider))
			for line in traceback.format_exc().split("\n"):
				self.log.warning(line)
			for _ in range(5):
				self.destroy_vm(vm_name)
				time.sleep(2.5)
		except Exception as e:
			self.interface.mon_con.incr("vm-create.{provider}.fail.unknown-error".format(provider=provider))
			self.log.error("Unknown failure instantiating VM %s!", vm_name)
			for line in traceback.format_exc().split("\n"):
				self.log.error(line)

			for _ in range(5):
				self.destroy_vm(vm_name)
				time.sleep(2.5)


		self.log.info("VM Creation complete.")
		self.interface.list_nodes()

	def destroy_vm(self, vm_name):
		self.interface.list_nodes()
		self.log.info("Destroying VM named: %s, current workers: %s", vm_name, [worker for provider, worker in self.interface.list_nodes()])
		dest_cnt = 0
		while vm_name in [worker for provider, worker in self.interface.list_nodes()]:
			self.interface.destroy_client(vm_name)
			dest_cnt += 1
		self.log.info("VM %s destroyed (%s calls).", vm_name, dest_cnt)
		self.interface.list_nodes()

	def build_target_vm_list(self):
		workers = []
		for x in range(settings.VPS_ACTIVE_WORKERS):
			# start VPS numbers at 1
			# Mostly for nicer printing
			workers.append(VPS_NAME_FORMAT.format(number=x+1))

		assert len(set(workers)) == len(workers), "Duplicate VPS target names: %s!" % workers
		return set(workers)


	def get_active_vms(self):
		# workers = ['scrape-worker-1', 'scrape-worker-2', 'scrape-worker-a', 'scrape-worker-5', 'utility']
		workers = self.interface.list_nodes()

		ret = []
		active_each = {}

		for provider, worker in workers:
			if worker.startswith('scrape-worker'):
				ret.append(worker)
				active_each.setdefault(provider, []).append(worker)


		workers = [worker for provider, worker in workers if worker.startswith('scrape-worker')]

		if len(set(workers)) != len(workers):
			self.log.error("Duplicate VPS target names in active workers: %s!", workers)
			for worker in set(workers):
				if workers.count(worker) > 1:
					self.log.info("Destroying VM: ")
					self.destroy_vm(worker)

		return set(workers)

	def worker_lister(self):
		'''
		Maximally dumb function to kick over the stats system.
		'''
		self.get_active_vms()

	def ensure_active_workers(self):
		self.log.info("Validating active VPSes")
		active = self.get_active_vms()

		self.log.info("Active nodes:")
		for node_tmp in active:
			self.log.info("	%s", node_tmp)

		target = self.build_target_vm_list()

		# Whoo set math!
		missing = target - active
		extra   = active - target

		self.log.info("Active managed VPSes: %s", active)
		self.log.info("Target VPS set      : %s", target)
		self.log.info("Need to create VMs  : %s", missing)
		self.log.info("Need to destroy VMs : %s", extra)

		for vm_name in extra:
			self.destroy_vm(vm_name)
		for vm_name in missing:
			self.create_vm(vm_name)

		existing = self.sched.get_jobs()
		for job in existing:
			self.log.info(" %s, %s", job, job.args)



	def install_destroyer_jobs(self):
		# vms = self.get_active_vms()
		vms = self.build_target_vm_list()
		hours = time.time() / (60 * 60)

		restart_interval = settings.VPS_LIFETIME_HOURS / settings.VPS_ACTIVE_WORKERS
		basetime = time.time()
		basetime = basetime - (basetime % hrs_to_sec(settings.VPS_LIFETIME_HOURS))

		print(hours % settings.VPS_LIFETIME_HOURS, restart_interval, basetime)
		for vm in vms:
			vm_num = int(vm.split("-")[-1])
			start_offset = vm_num * restart_interval
			nextrun = basetime + hrs_to_sec(start_offset)

			# Don't schedule a destruction before we start the scheduler.
			if nextrun+120 < time.time():
				nextrun += hrs_to_sec(settings.VPS_LIFETIME_HOURS)

			self.sched.add_job(self.destroy_vm,
				trigger       = 'interval',
				args          = (vm, ),
				seconds       = hrs_to_sec(settings.VPS_LIFETIME_HOURS),
				next_run_time = datetime.datetime.fromtimestamp(nextrun, tz=pytz.utc))
			print("Item nextrun: ", nextrun, nextrun - time.time())

	def run(self):
		self.sched.start()

def refresh():
	sched = VpsScheduler()
	vm_names = sched.get_active_vms()
	print("Active VMs to refresh:", vm_names)
	for vm_name in vm_names:
		print("Reconstructing %s" % vm_name)
		sched.destroy_vm(vm_name)
		sched.ensure_active_workers()

def run_scheduler():

	sched = VpsScheduler()

	print("Sched: ", sched)

	sched.ensure_active_workers()
	sched.run()

def run():

	proc = None
	last_zero = time.time()


	new_create_timeout_secs = hrs_to_sec(settings.VPS_LIFETIME_HOURS + 1.5)


	while 1:
		# If there's no thread, create it.
		if proc is None:
			print("Thread is none. Creating.")
			proc = multiprocessing.Process(target=run_scheduler)
			proc.start()
			CREATE_WATCHDOG.value = 0
			last_zero = time.time()

		try:
			state = proc.is_alive()
		except Exception:
			traceback.print_exc()
			state = "Failed to get"


		print("Watchdog looping! Value: %s, last update: %s/%s ago, thread: %s->%s" % (CREATE_WATCHDOG.value, int(time.time() - last_zero), new_create_timeout_secs, state, proc))
		# If the worker has touched the watchdog flag, capture the
		# time that happened.
		if CREATE_WATCHDOG.value != 0:
			last_zero = time.time()
			CREATE_WATCHDOG.value = 0

		# If the last worker update time is longer ago then the timeout,
		# destroy the worker thread.
		if (time.time() - last_zero) > new_create_timeout_secs:
			print("Terminating thread!")

			try:
				while proc.is_alive():
					print("Trying!")
					proc.terminate()
					proc.join(timeout=1.0)
			except Exception:
				print("Exception in terminate!")
				traceback.print_exc()

			proc = None

		time.sleep(5)


if __name__ == '__main__':
	logSetup.initLogging()

	if 'refresh' in sys.argv:
		refresh()
	else:
		run()

