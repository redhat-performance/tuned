import tuned.plugins
import tuned.logs
import tuned.monitors
import os
import struct
import glob
from subprocess import *

log = tuned.logs.get()

class KTunePlugin(tuned.plugins.Plugin):
	"""
	"""

	def __init__(self, devices, options):
		"""
		"""
		super(self.__class__, self).__init__(None, options)
		self._updated = False
		self._scripts = []
		self._load_ktuned()
		self._scripts.append(self._options["script"])

	@classmethod
	def _get_default_options(cls):
		# TODO: match cciss* somehow
		return {
			"elevator" : "",
			"script"   : "",
			"elevator_devs"   : "/sys/block/sd*/queue/scheduler",
		}

	def _load_ktuned(self):
		for sh in glob.glob("/etc/ktune.d/*.sh"):
			script = os.path.join("/etc/ktune.d/", sh)
			if not script in self._scripts:
				self._scripts.append(script)
		return True

	def _apply_elevator(self):
		for dev in glob.glob(self._options["elevator_devs"]):
			log.debug("Applying elevator: %s < %s" % (dev, self._options["elevator"]))
			try:
				f = open(dev, "w")
				f.write(self._options["elevator"])
				f.close()
			except (OSError,IOError) as e:
				log.error("Setting elevator on %s error: %s" % (dev, e))
		return True

	def _revert_elevator(self):
		for dev in glob.glob(self._options["elevator_devs"]):
			log.debug("Applying elevator: %s < cfs" % (dev))
			try:
				f = open(dev, "w")
				f.write("cfs")
				f.close()
			except (OSError,IOError) as e:
				log.error("Setting elevator on %s error: %s" % (dev, e))

	def _call_scripts(self, arg = "start"):
		for script in self._scripts:
			log.info("Calling script %s" % (script))
			try:
				proc = Popen([script, arg], stdout=PIPE, stderr=PIPE)
				out, err = proc.communicate()

				if proc.returncode:
					log.error("script %s error: %s" % (script, err[:-1]))
			except (OSError,IOError) as e:
				log.error("Script %s error: %s" % (script, e))
		return True

	def cleanup(self):
		self._revert_elevator()
		self._call_scripts("stop")

	def update_tuning(self):
		if self._updated:
			return

		self._updated = True
		self._apply_elevator()
		self._call_scripts()
