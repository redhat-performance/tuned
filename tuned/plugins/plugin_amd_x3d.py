import glob
import errno

from . import base
from .decorators import *
import tuned.logs

log = tuned.logs.get()

_X3D_MODE_GLOB = "/sys/bus/platform/drivers/amd_x3d_vcache/*/amd_x3d_mode"
_VALID_MODES = frozenset(["cache", "frequency"])


def _find_x3d_paths():
	"""Return discovered amd_x3d_mode sysfs paths in a stable order."""
	return sorted(glob.glob(_X3D_MODE_GLOB))


class AMDX3DPlugin(base.Plugin):
	"""
	Controls the AMD 3D V-Cache scheduling mode on dual-CCD processors
	such as Ryzen 9 7950X3D, 7900X3D, 9950X3D, and 9900X3D processors.

	The [option]`mode` option configures the `amd_x3d_vcache` kernel
	driver. The driver exposes a sysfs knob that biases the scheduler
	towards one CCD or the other:

	* `cache`
	+
	Prefer the CCD with 3D V-Cache. This is useful for games and other
	cache-sensitive workloads.

	* `frequency`
	+
	Prefer the non-X3D CCD, which can usually boost higher. This is
	useful for throughput-oriented compute workloads and is the kernel
	default.

	The plugin discovers the sysfs path using a glob because the ACPI
	device name can vary across boards. On systems without the
	`amd_x3d_vcache` driver or without a supported dual-CCD X3D CPU, the
	plugin does nothing.

	.Prefer the X3D CCD for games
	====
	----
	[amd_x3d]
	mode=cache
	----
	====

	.Prefer the higher-frequency CCD for compute workloads
	====
	----
	[amd_x3d]
	mode=frequency
	----
	====
	"""

	@classmethod
	def _get_config_options(cls):
		return {
			"mode": None,
		}

	def _instance_init(self, instance):
		instance._has_static_tuning = True
		instance._has_dynamic_tuning = False

	def _instance_cleanup(self, instance):
		pass

	def _x3d_paths(self):
		return _find_x3d_paths()

	@command_set("mode")
	def _set_mode(self, value, instance, sim, remove):
		if value not in _VALID_MODES:
			if not sim:
				log.warning("amd_x3d: invalid mode '%s', expected one of: %s"
						% (value, ", ".join(sorted(_VALID_MODES))))
			return None

		paths = self._x3d_paths()
		if not paths:
			if not sim:
				log.debug("amd_x3d: no AMD 3D V-Cache device found, skipping")
			return None

		if not sim:
			for path in paths:
				log.info("amd_x3d: setting mode to '%s' on %s" % (value, path))
				self._cmd.write_to_file(path, value,
						no_error=[errno.ENOENT] if remove else False)
		return value

	@command_get("mode")
	def _get_mode(self, instance):
		paths = self._x3d_paths()
		if not paths:
			return None

		# All CCD pairs share the same mode; read from the first found path.
		data = self._cmd.read_file(paths[0]).strip()
		if not data:
			return None
		return self._cmd.get_active_option(data)
