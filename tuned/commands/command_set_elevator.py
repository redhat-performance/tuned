import tuned.commands
import tuned.logs
import os
import struct

log = tuned.logs.get()

class SetElevatorCommand(tuned.commands.Command):
	"""
	"""

	def __init__(self):
		"""
		"""
		super(self.__class__, self).__init__("set_elevator")

	def execute(self, args):
		dev = args[0];
		elevator = args[1]
		old_args = [dev, ""]

		try:
			f = open(os.path.join("/sys/block/", dev, "queue/scheduler"), "r")
			old_args[1] = f.read()
			f.close()
		except (OSError,IOError) as e:
			log.error("Getting elevator of %s error: %s" % (dev, e))

		log.debug("Applying elevator: %s < %s" % (dev, elevator))
		try:
			f = open(os.path.join("/sys/block/", dev, "queue/scheduler"), "w")
			f.write(elevator)
			f.close()
		except (OSError,IOError) as e:
			log.error("Setting elevator on %s error: %s" % (dev, e))
		return old_args

	def revert(self, args):
		self.execute(args)
