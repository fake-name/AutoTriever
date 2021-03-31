

from . import NuJob

def minutes(count):
	return count * 60
def hours(count):
	return count * minutes(60)
def days(count):
	return count * hours(24)


JOBS = [
	(NuJob.NuMonitor,            "NuJob",            minutes(45)),
]
