
import time
import pytz
import logging
import datetime
from apscheduler.schedulers.blocking import BlockingScheduler
import sys
import settings
import traceback

import logSetup
import marshaller_exceptions
import stopit

if "test" in sys.argv:
	import salt_dummy as salt_runner
else:
	import salt_runner


VPS_NAME_FORMAT = "scrape-worker-{number}"

def hrs_to_sec(in_val):
	return in_val * 60 * 60

def poke_statsd():
	interface = salt_runner.VpsHerder()
	interface.list_nodes()


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

		self.log.info("Creating VM named: %s, index: %s", vm_name, vm_idx)
		try:
			# VM Create time is 30 minutes, max
			with stopit.ThreadingTimeout(60 * 30, swallow_exc=False):
				# This is slightly horrible.
				with self.interface.mon_con.timer("VM-Creation"):
					self.interface.make_client(vm_name)
					self.interface.configure_client(vm_name, vm_idx)
				self.log.info("VM %s created.", vm_name)
		except stopit.TimeoutException:
			self.log.info("Timeout instantiating VM %s.", vm_name)
			traceback.print_exc()
			self.destroy_vm(vm_name)
		except marshaller_exceptions.VmCreateFailed:
			self.log.info("Failure instantiating VM %s.", vm_name)
			traceback.print_exc()
			self.destroy_vm(vm_name)

		self.interface.list_nodes()

	def destroy_vm(self, vm_name):
		self.interface.list_nodes()
		self.log.info("Destroying VM named: %s", vm_name)
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
		self.log.info("Active managed VPSes: %s", active)
		self.log.info("Target VPS set: %s", target)

		# Whoo set math!
		missing = target - active
		extra   = active - target
		self.log.info("Need to create VMs: %s", missing)
		self.log.info("Need to destroy VMs: %s", extra)

		for vm_name in extra:
			self.destroy_vm(vm_name)
		for vm_name in missing:
			self.create_vm(vm_name)

		existing = self.sched.get_jobs()
		tznow = datetime.datetime.now(tz=pytz.utc)
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

if __name__ == '__main__':
	logSetup.initLogging()

	if 'refresh' in sys.argv:
		refresh()
	else:
		run_scheduler()

