import base
from decorators import *
import tuned.logs
from tuned.utils.commands import commands
import tuned.consts as consts

import os
import re

log = tuned.logs.get()

class BootloaderPlugin(base.Plugin):
	"""
	Plugin for tuning bootloader options.

	Currently only grub2 is supported and reboot is required to apply the tunings.
	These tunings are unloaded only on profile change followed by reboot.
	"""

	def __init__(self, *args, **kwargs):
		super(self.__class__, self).__init__(*args, **kwargs)
		self._cmd = commands()

	def _instance_init(self, instance):
		instance._has_dynamic_tuning = False
		instance._has_static_tuning = True
		self._grub2_cfg_file = self._get_grub2_cfg_file()

	def _instance_cleanup(self, instance):
		pass

	def _get_config_options(cls):
		return {
			"grub2_cfg_file": None,
			"cmdline": "",
		}

	def _get_grub2_cfg_file(self):
		for f in consts.GRUB2_CFG_FILES:
			if os.path.exists(f):
				return f
		return None

	def _patch_bootcmdline(self, value):
		return self._cmd.replace_in_file(consts.BOOT_CMDLINE_FILE, r"\b(" + consts.BOOT_CMDLINE_TUNED_VAR + \
			r"\s*=).*$", r"\1" + "\"" + str(value) + "\"")

	def _remove_grub2_tuning(self):
		self._patch_bootcmdline("")
		self._cmd.replace_in_file(self._grub2_cfg_file, r"\b(set " + consts.GRUB2_TUNED_VAR + r"\s*=).*$", r"\1")

	def _instance_unapply_static(self, instance, profile_switch = False):
		if profile_switch:
			log.info("removing grub2 command line previously added by tuned")
			self._remove_grub2_tuning()

	def _grub2_cfg_unpatch(self, grub2_cfg):
		log.debug("unpatching grub.cfg")
		cfg = re.sub(r"\bset " + consts.GRUB2_TUNED_VAR + "\s*=.*$", "", grub2_cfg, flags = re.MULTILINE)
		grub2_cfg = re.sub(r"\$" + consts.GRUB2_TUNED_VAR, "", cfg, flags = re.MULTILINE)
		cfg = re.sub(consts.GRUB2_TEMPLATE_HEADER_BEGIN, "", grub2_cfg, flags = re.MULTILINE)
		return re.sub(consts.GRUB2_TEMPLATE_HEADER_END, "", cfg, flags = re.MULTILINE)

	def _grub2_cfg_patch_initial(self, grub2_cfg, value):
		log.debug("initial patching of grub.cfg")
		cfg = re.sub(r"^(\s*###\s+END\s+[^#]+/00_header\s+###\s*)$", r"\1" + "\n" + consts.GRUB2_TEMPLATE_HEADER_BEGIN + "\nset " +
			consts.GRUB2_TUNED_VAR + "=\"" + str(value) + "\"\n" + consts.GRUB2_TEMPLATE_HEADER_END + "\n", grub2_cfg, flags = re.MULTILINE)
		return re.sub(r"^(\s*linux(16|efi)\s+.*)$", r"\1 $" + consts.GRUB2_TUNED_VAR, cfg, flags = re.MULTILINE)

	def _grub2_default_env_patch(self):
		grub2_default_env = self._cmd.read_file(consts.GRUB2_DEFAULT_ENV_FILE)
		if len(grub2_default_env) <= 0:
			log.error("error reading '%s'" % consts.GRUB2_DEFAULT_ENV_FILE)
			return False

		if re.search(r"^[^#]*\bGRUB_CMDLINE_LINUX\s*=.*\\\$" + consts.GRUB2_TUNED_VAR + r"\b.*$", grub2_default_env, flags = re.MULTILINE) is None:
			log.debug("patching '%s'" % consts.GRUB2_DEFAULT_ENV_FILE)
			self._cmd.write_to_file(consts.GRUB2_DEFAULT_ENV_FILE,
				grub2_default_env + "GRUB_CMDLINE_LINUX=\"$GRUB_CMDLINE_LINUX " + r"\$" + consts.GRUB2_TUNED_VAR + "\"\n")
		return True

	def _grub2_cfg_patch(self, value):
		log.debug("patching grub.cfg")
		if self._grub2_cfg_file is None:
			log.error("cannot find grub.cfg to patch, you need to regenerate it by hand by grub2-mkconfig")
			return False
		grub2_cfg = self._cmd.read_file(self._grub2_cfg_file)
		if len(grub2_cfg) <= 0:
			log.error("error patching %s, you need to regenerate it by hand by grub2-mkconfig" % self._grub2_cfg_file)
			return False
		log.debug("adding boot command line parameters to '%s'" % self._grub2_cfg_file)
		(grub2_cfg_new, nsubs) = re.subn(r"\b(set " + consts.GRUB2_TUNED_VAR + "\s*=).*$", r"\1" + "\"" + str(value) + "\"", grub2_cfg, flags = re.MULTILINE)
		if nsubs < 1:
			grub2_cfg_new = self._grub2_cfg_patch_initial(self._grub2_cfg_unpatch(grub2_cfg), value)
		self._cmd.write_to_file(self._grub2_cfg_file, grub2_cfg_new)
		self._grub2_default_env_patch()
		return True

	@command_custom("grub2_cfg_file")
	def _grub2_cfg_file(self, enabling, value):
		if enabling and value is not None:
			self._grub2_cfg_file = value

	@command_custom("cmdline", per_device = False, priority = 10)
	def _cmdline(self, enabling, value):
		if enabling:
			log.info("installing additional boot command line parameters to grub2")
			self._grub2_cfg_patch(value)
			self._patch_bootcmdline(value)
