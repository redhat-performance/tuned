from . import base
from .decorators import *
import tuned.logs
from . import exceptions
from tuned.utils.commands import commands
import tuned.consts as consts

import os
import re
import tempfile

log = tuned.logs.get()

class BootloaderPlugin(base.Plugin):
	"""
	Plugin for tuning bootloader options.

	Currently only grub2 is supported and reboot is required to apply the tunings.
	These tunings are unloaded only on profile change followed by reboot.
	"""

	def __init__(self, *args, **kwargs):
		if not os.path.isfile(consts.GRUB2_TUNED_TEMPLATE_PATH):
			raise exceptions.NotSupportedPluginException("Required GRUB2 template not found, disabling plugin.")
		super(BootloaderPlugin, self).__init__(*args, **kwargs)
		self._cmd = commands()

	def _instance_init(self, instance):
		instance._has_dynamic_tuning = False
		instance._has_static_tuning = True
		# controls grub2_cfg rewrites in _instance_post_static
		self.update_grub2_cfg = False
		self._initrd_remove_dir = False
		self._initrd_dst_img_val = None
		self._cmdline_val = ""
		self._initrd_val = ""
		self._grub2_cfg_file_names = self._get_grub2_cfg_files()

	def _instance_cleanup(self, instance):
		pass

	@classmethod
	def _get_config_options(cls):
		return {
			"grub2_cfg_file": None,
			"initrd_dst_img": None,
			"initrd_add_img": None,
			"initrd_add_dir": None,
			"initrd_remove_dir": None,
			"cmdline": None,
		}

	def _get_effective_options(self, options):
		"""Merge provided options with plugin default options and merge all cmdline.* options."""
		effective = self._get_config_options().copy()
		cmdline_keys = []
		for key in options:
			if str(key).startswith("cmdline"):
				cmdline_keys.append(key)
			elif key in effective:
				effective[key] = options[key]
			else:
				log.warn("Unknown option '%s' for plugin '%s'." % (key, self.__class__.__name__))
		cmdline_keys.sort()
		cmdline = ""
		for key in cmdline_keys:
			val = options[key]
			if val is None or val == "":
				continue
			op = val[0]
			vals = val[1:].strip()
			if op == "+" and vals != "":
				cmdline += " " + vals
			elif op == "-" and vals != "":
				for p in vals.split():
					regex = re.escape(p)
					cmdline = re.sub(r"(\A|\s)" + regex + r"(?=\Z|\s)", r"", cmdline)
			else:
				cmdline += " " + val
		cmdline = cmdline.strip()
		if cmdline != "":
			effective["cmdline"] = cmdline
		return effective

	def _get_grub2_cfg_files(self):
		cfg_files = []
		for f in consts.GRUB2_CFG_FILES:
			if os.path.exists(f):
				cfg_files.append(f)
		return cfg_files

	def _patch_bootcmdline(self, d):
		return self._cmd.add_modify_option_in_file(consts.BOOT_CMDLINE_FILE, d)

	def _remove_grub2_tuning(self):
		if not self._grub2_cfg_file_names:
			log.error("cannot find grub.cfg to patch, you need to regenerate it by hand using grub2-mkconfig")
			return
		self._patch_bootcmdline({consts.BOOT_CMDLINE_TUNED_VAR : "", consts.BOOT_CMDLINE_INITRD_ADD_VAR : ""})
		for f in self._grub2_cfg_file_names:
			self._cmd.add_modify_option_in_file(f, {"set\s+" + consts.GRUB2_TUNED_VAR : "", "set\s+" + consts.GRUB2_TUNED_INITRD_VAR : ""}, add = False)
		if self._initrd_dst_img_val is not None:
			log.info("removing initrd image '%s'" % self._initrd_dst_img_val)
			self._cmd.unlink(self._initrd_dst_img_val)

	def _instance_unapply_static(self, instance, full_rollback = False):
		if full_rollback:
			log.info("removing grub2 tuning previously added by Tuned")
			self._remove_grub2_tuning()

	def _grub2_cfg_unpatch(self, grub2_cfg):
		log.debug("unpatching grub.cfg")
		cfg = re.sub(r"^\s*set\s+" + consts.GRUB2_TUNED_VAR + "\s*=.*\n", "", grub2_cfg, flags = re.MULTILINE)
		grub2_cfg = re.sub(r" *\$" + consts.GRUB2_TUNED_VAR, "", cfg, flags = re.MULTILINE)
		cfg = re.sub(r"^\s*set\s+" + consts.GRUB2_TUNED_INITRD_VAR + "\s*=.*\n", "", grub2_cfg, flags = re.MULTILINE)
		grub2_cfg = re.sub(r" *\$" + consts.GRUB2_TUNED_INITRD_VAR, "", cfg, flags = re.MULTILINE)
		cfg = re.sub(consts.GRUB2_TEMPLATE_HEADER_BEGIN + r"\n", "", grub2_cfg, flags = re.MULTILINE)
		return re.sub(consts.GRUB2_TEMPLATE_HEADER_END + r"\n+", "", cfg, flags = re.MULTILINE)

	def _grub2_cfg_patch_initial(self, grub2_cfg, d):
		log.debug("initial patching of grub.cfg")
		s = r"\1\n\n" + consts.GRUB2_TEMPLATE_HEADER_BEGIN + "\n"
		for opt in d:
			s += r"set " + self._cmd.escape(opt) + "=\"" + self._cmd.escape(d[opt]) + "\"\n"
		s += consts.GRUB2_TEMPLATE_HEADER_END + r"\n"
		grub2_cfg = re.sub(r"^(\s*###\s+END\s+[^#]+/00_header\s+### *)\n", s, grub2_cfg, flags = re.MULTILINE)

		d2 = {"linux" : consts.GRUB2_TUNED_VAR, "initrd" : consts.GRUB2_TUNED_INITRD_VAR}
		for i in d2:
			# add tuned parameters to all kernels
			grub2_cfg = re.sub(r"^(\s*" + i + r"(16|efi)?\s+.*)$", r"\1 $" + d2[i], grub2_cfg, flags = re.MULTILINE)
			# remove tuned parameters from rescue kernels
			grub2_cfg = re.sub(r"^(\s*" + i + r"(?:16|efi)?\s+\S+rescue.*)\$" + d2[i] + r" *(.*)$", r"\1\2", grub2_cfg, flags = re.MULTILINE)
			# fix whitespaces in rescue kernels
			grub2_cfg = re.sub(r"^(\s*" + i + r"(?:16|efi)?\s+\S+rescue.*) +$", r"\1", grub2_cfg, flags = re.MULTILINE)
		return grub2_cfg

	def _grub2_default_env_patch(self):
		grub2_default_env = self._cmd.read_file(consts.GRUB2_DEFAULT_ENV_FILE)
		if len(grub2_default_env) <= 0:
			log.error("error reading '%s'" % consts.GRUB2_DEFAULT_ENV_FILE)
			return False

		d = {"GRUB_CMDLINE_LINUX_DEFAULT" : consts.GRUB2_TUNED_VAR, "GRUB_INITRD_OVERLAY" : consts.GRUB2_TUNED_INITRD_VAR}
		write = False
		for i in d:
			if re.search(r"^[^#]*\b" + i + r"\s*=.*\\\$" + d[i] + r"\b.*$", grub2_default_env, flags = re.MULTILINE) is None:
				write = True
				if grub2_default_env[-1] != "\n":
					grub2_default_env += "\n"
				grub2_default_env += i + "=\"${" + i + ":+$" + i + r" }\$" + d[i] + "\"\n"
		if write:
			log.debug("patching '%s'" % consts.GRUB2_DEFAULT_ENV_FILE)
			self._cmd.write_to_file(consts.GRUB2_DEFAULT_ENV_FILE, grub2_default_env)
		return True

	def _grub2_cfg_patch(self, d):
		log.debug("patching grub.cfg")
		if not self._grub2_cfg_file_names:
			log.error("cannot find grub.cfg to patch, you need to regenerate it by hand by grub2-mkconfig")
			return False
		for f in self._grub2_cfg_file_names:
			grub2_cfg = self._cmd.read_file(f)
			if len(grub2_cfg) <= 0:
				log.error("error patching %s, you need to regenerate it by hand by grub2-mkconfig" % f)
				return False
			log.debug("adding boot command line parameters to '%s'" % f)
			grub2_cfg_new = grub2_cfg
			patch_initial = False
			for opt in d:
				(grub2_cfg_new, nsubs) = re.subn(r"\b(set\s+" + opt + "\s*=).*$", r"\1" + "\"" + d[opt] + "\"", grub2_cfg_new, flags = re.MULTILINE)
				if nsubs < 1 or re.search(r"\$" + opt, grub2_cfg, flags = re.MULTILINE) is None:
					patch_initial = True

			# workaround for rhbz#1442117
			if len(re.findall(r"\$" + consts.GRUB2_TUNED_VAR, grub2_cfg, flags = re.MULTILINE)) != \
				len(re.findall(r"\$" + consts.GRUB2_TUNED_INITRD_VAR, grub2_cfg, flags = re.MULTILINE)):
					patch_initial = True

			if patch_initial:
				grub2_cfg_new = self._grub2_cfg_patch_initial(self._grub2_cfg_unpatch(grub2_cfg), d)
			self._cmd.write_to_file(f, grub2_cfg_new)
		self._grub2_default_env_patch()
		return True

	def _grub2_update(self):
		self._grub2_cfg_patch({consts.GRUB2_TUNED_VAR : self._cmdline_val, consts.GRUB2_TUNED_INITRD_VAR : self._initrd_val})
		self._patch_bootcmdline({consts.BOOT_CMDLINE_TUNED_VAR : self._cmdline_val, consts.BOOT_CMDLINE_INITRD_ADD_VAR : self._initrd_val})

	def _init_initrd_dst_img(self, name):
		if self._initrd_dst_img_val is None:
			self._initrd_dst_img_val = os.path.join(consts.BOOT_DIR, os.path.basename(name))

	def _check_petitboot(self):
		return os.path.isdir(consts.PETITBOOT_DETECT_DIR)

	def _install_initrd(self, img):
		if self._check_petitboot():
			log.warn("Detected Petitboot which doesn't support initrd overlays. The initrd overlay will be ignored by bootloader.")
		log.info("installing initrd image as '%s'" % self._initrd_dst_img_val)
		img_name = os.path.basename(self._initrd_dst_img_val)
		if not self._cmd.copy(img, self._initrd_dst_img_val):
			return False
		self.update_grub2_cfg = True
		curr_cmdline = self._cmd.read_file("/proc/cmdline").rstrip()
		initrd_grubpath = "/"
		lc = len(curr_cmdline)
		if lc:
			path = re.sub(r"^\s*BOOT_IMAGE=\s*(\S*/).*$", "\\1", curr_cmdline)
			if len(path) < lc:
				initrd_grubpath = path
		self._initrd_val = os.path.join(initrd_grubpath, img_name)
		return True

	@command_custom("grub2_cfg_file")
	def _grub2_cfg_file(self, enabling, value, verify, ignore_missing):
		# nothing to verify
		if verify:
			return None
		if enabling and value is not None:
			self._grub2_cfg_file_names = [str(value)]

	@command_custom("initrd_dst_img")
	def _initrd_dst_img(self, enabling, value, verify, ignore_missing):
		# nothing to verify
		if verify:
			return None
		if enabling and value is not None:
			self._initrd_dst_img_val = str(value)
			if self._initrd_dst_img_val == "":
				return False
			if self._initrd_dst_img_val[0] != "/":
				self._initrd_dst_img_val = os.path.join(consts.BOOT_DIR, self._initrd_dst_img_val)

	@command_custom("initrd_remove_dir")
	def _initrd_remove_dir(self, enabling, value, verify, ignore_missing):
		# nothing to verify
		if verify:
			return None
		if enabling and value is not None:
			self._initrd_remove_dir = self._cmd.get_bool(value) == "1"

	@command_custom("initrd_add_img", per_device = False, priority = 10)
	def _initrd_add_img(self, enabling, value, verify, ignore_missing):
		# nothing to verify
		if verify:
			return None
		if enabling and value is not None:
			src_img = str(value)
			self._init_initrd_dst_img(src_img)
			if src_img == "":
				return False
			if not self._install_initrd(src_img):
				return False

	@command_custom("initrd_add_dir", per_device = False, priority = 10)
	def _initrd_add_dir(self, enabling, value, verify, ignore_missing):
		# nothing to verify
		if verify:
			return None
		if enabling and value is not None:
			src_dir = str(value)
			self._init_initrd_dst_img(src_dir)
			if src_dir == "":
				return False
			if not os.path.isdir(src_dir):
				log.error("error: cannot create initrd image, source directory '%s' doesn't exist" % src_dir)
				return False

			log.info("generating initrd image from directory '%s'" % src_dir)
			(fd, tmpfile) = tempfile.mkstemp(prefix = "tuned-bootloader-", suffix = ".tmp")
			log.debug("writing initrd image to temporary file '%s'" % tmpfile)
			os.close(fd)
			(rc, out) = self._cmd.execute("find . | cpio -co > %s" % tmpfile, cwd = src_dir, shell = True)
			log.debug("cpio log: %s" % out)
			if rc != 0:
				log.error("error generating initrd image")
				self._cmd.unlink(tmpfile, no_error = True)
				return False
			self._install_initrd(tmpfile)
			self._cmd.unlink(tmpfile)
			if self._initrd_remove_dir:
				log.info("removing directory '%s'" % src_dir)
				self._cmd.rmtree(src_dir)

	@command_custom("cmdline", per_device = False, priority = 10)
	def _cmdline(self, enabling, value, verify, ignore_missing):
		v = self._variables.expand(self._cmd.unquote(value))
		if verify:
			cmdline = self._cmd.read_file("/proc/cmdline")
			if len(cmdline) == 0:
				return None
			cmdline_set = set(cmdline.split())
			value_set = set(v.split())
			cmdline_intersect = cmdline_set.intersection(value_set)
			if cmdline_intersect == value_set:
				log.info(consts.STR_VERIFY_PROFILE_VALUE_OK % ("cmdline", str(value_set)))
				return True
			else:
				log.error(consts.STR_VERIFY_PROFILE_VALUE_FAIL % ("cmdline", str(cmdline_intersect), str(value_set)))
				return False
		if enabling and value is not None:
			log.info("installing additional boot command line parameters to grub2")
			self.update_grub2_cfg = True
			self._cmdline_val = v

	def _instance_post_static(self, instance, enabling):
		if enabling and self.update_grub2_cfg:
			self._grub2_update()
			self.update_grub2_cfg = False
