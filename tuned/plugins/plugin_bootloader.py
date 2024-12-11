from . import base
from .decorators import *
import tuned.logs
from . import exceptions
from tuned.utils.commands import commands
import tuned.consts as consts

import os
import re
import tempfile
from time import sleep

log = tuned.logs.get()

class BootloaderPlugin(base.Plugin):
	"""
	Adds options to the kernel command line. This plug-in supports the
	GRUB 2 boot loader and the Boot Loader Specification (BLS).

	NOTE: *TuneD* will not remove or replace kernel command line
	parameters added via other methods like *grubby*. *TuneD* will manage
	the kernel command line parameters added via *TuneD*. Please refer
	to your platform bootloader documentation about how to identify and
	manage kernel command line parameters set outside of *TuneD*.

	Customized non-standard location of the GRUB 2 configuration file
	can be specified by the [option]`grub2_cfg_file` option.

	The kernel options are added to the current GRUB configuration and
	its templates. Reboot the system for the kernel option to take effect.

	Switching to another profile or manually stopping the `tuned`
	service removes the additional options. If you shut down or reboot
	the system, the kernel options persist in the [filename]`grub.cfg`
	file and grub environment files.

	The kernel options can be specified by the following syntax:

	[subs="+quotes,+macros"]
	----
	cmdline__suffix__=__arg1__ __arg2__ ... __argN__
	----

	Or with an alternative, but equivalent syntax:

	[subs="+quotes,+macros"]
	----
	cmdline__suffix__=+__arg1__ __arg2__ ... __argN__
	----

	Where __suffix__ can be arbitrary (even empty) alphanumeric
	string which should be unique across all loaded profiles. It is
	recommended to use the profile name as the __suffix__
	(for example, [option]`cmdline_my_profile`). If there are multiple
	[option]`cmdline` options with the same suffix, during the profile
	load/merge the value which was assigned previously will be used. This
	is the same behavior as any other plug-in options. The final kernel
	command line is constructed by concatenating all the resulting
	[option]`cmdline` options.

	It is also possible to remove kernel options by the following syntax:

	[subs="+quotes,+macros"]
	----
	cmdline__suffix__=-__arg1__ __arg2__ ... __argN__
	----

	Such kernel options will not be concatenated and thus removed during
	the final kernel command line construction.

	.Modifying the kernel command line
	====
	For example, to add the [option]`quiet` kernel option to a *TuneD*
	profile, include the following lines in the [filename]`tuned.conf`
	file:
	----
	[bootloader]
	cmdline_my_profile=+quiet
	----
	An example of a custom profile `my_profile` that adds the
	[option]`isolcpus=2` option to the kernel command line:
	----
	[bootloader]
	cmdline_my_profile=isolcpus=2
	----
	An example of a custom profile `my_profile` that removes the
	[option]`rhgb quiet` options from the kernel command line (if
	previously added by *TuneD*):
	----
	[bootloader]
	cmdline_my_profile=-rhgb quiet
	----
	====

	.Modifying the kernel command line, example with inheritance
	====
	For example, to add the [option]`rhgb quiet` kernel options to a
	*TuneD* profile `profile_1`:
	----
	[bootloader]
	cmdline_profile_1=+rhgb quiet
	----
	In the child profile `profile_2` drop the [option]`quiet` option
	from the kernel command line:
	----
	[main]
	include=profile_1
	
	[bootloader]
	cmdline_profile_2=-quiet
	----
	The final kernel command line will be [option]`rhgb`. In case the same
	[option]`cmdline` suffix as in the `profile_1` is used:
	----
	[main]
	include=profile_1
	
	[bootloader]
	cmdline_profile_1=-quiet
	----
	It will result in the empty kernel command line because the merge
	executes and the [option]`cmdline_profile_1` gets redefined to just
	[option]`-quiet`. Thus there is nothing to remove in the final kernel
	command line processing.
	====

	The [option]`initrd_add_img=IMAGE` adds an initrd overlay file
	`IMAGE`. If the `IMAGE` file name begins with '/', the absolute path is
	used. Otherwise, the current profile directory is used as the base
	directory for the `IMAGE`.

	The [option]`initrd_add_dir=DIR` creates an initrd image from the
	directory `DIR` and adds the resulting image as an overlay.
	If the `DIR` directory name begins with '/', the absolute path
	is used. Otherwise, the current profile directory is used as the
	base directory for the `DIR`.

	The [option]`initrd_dst_img=PATHNAME` sets the name and location of
	the resulting initrd image. Typically, it is not necessary to use this
	option. By default, the location of initrd images is `/boot` and the
	name of the image is taken as the basename of `IMAGE` or `DIR`. This can
	be overridden by setting [option]`initrd_dst_img`.

	The [option]`initrd_remove_dir=VALUE` removes the source directory
	from which the initrd image was built if `VALUE` is true. Only 'y',
	'yes', 't', 'true' and '1' (case insensitive) are accepted as true
	values for this option. Other values are interpreted as false.

	.Adding an overlay initrd image
	====
	----
	[bootloader]
	initrd_remove_dir=True
	initrd_add_dir=/tmp/tuned-initrd.img
	----
	This creates an initrd image from the `/tmp/tuned-initrd.img` directory
	and and then removes the `tuned-initrd.img` directory from `/tmp`.
	====

	The [option]`skip_grub_config=VALUE` does not change grub
	configuration if `VALUE` is true. However, [option]`cmdline`
	options are still processed, and the result is used to verify the current
	cmdline. Only 'y', 'yes', 't', 'true' and '1' (case insensitive) are accepted
	as true values for this option. Other values are interpreted as false.

	.Do not change grub configuration
	====
	----
	[bootloader]
	skip_grub_config=True
	cmdline=+systemd.cpu_affinity=1
	----
	====
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
		self._skip_grub_config_val = False
		self._initrd_remove_dir = False
		self._initrd_dst_img_val = None
		self._cmdline_val = ""
		self._initrd_val = ""
		self._grub2_cfg_file_names = self._get_grub2_cfg_files()
		self._bls = self._bls_enabled()

		self._rpm_ostree = self._rpm_ostree_status() is not None

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
			"skip_grub_config": None,
		}

	@staticmethod
	def _options_to_dict(options, omit=""):
		"""
		Returns dict created from options
		e.g.: _options_to_dict("A=A A=B A B=A C=A", "A=B B=A B=B") returns {'A': ['A', None], 'C': ['A']}
		"""
		d = {}
		omit = omit.split()
		for o in options.split():
			if o not in omit:
				arr = o.split('=', 1)
				d.setdefault(arr[0], []).append(arr[1] if len(arr) > 1 else None)
		return d

	@staticmethod
	def _dict_to_options(d):
		return " ".join([k + "=" + v1 if v1 is not None else k for k, v in d.items() for v1 in v])

	def _rpm_ostree_status(self):
		"""
		Returns status of rpm-ostree transactions or None if not run on rpm-ostree system
		"""
		(rc, out, err) = self._cmd.execute(['rpm-ostree', 'status'], return_err=True)
		log.debug("rpm-ostree status output stdout:\n%s\nstderr:\n%s" % (out, err))
		if rc != 0:
			return None
		splited = out.split()
		if len(splited) < 2 or splited[0] != "State:":
			log.warning("Exceptional format of rpm-ostree status result:\n%s" % out)
			return None
		return splited[1]

	def _wait_till_idle(self):
		sleep_cycles = 10
		sleep_secs = 1.0
		for i in range(sleep_cycles):
			if self._rpm_ostree_status() == "idle":
				return True
			sleep(sleep_secs)
		if self._rpm_ostree_status() == "idle":
			return True
		return False

	def _rpm_ostree_kargs(self, append={}, delete={}):
		"""
		Method for appending or deleting rpm-ostree karg
		returns None if rpm-ostree not present or is run on not ostree system
		or tuple with new kargs, appended kargs and deleted kargs
		"""
		(rc, out, err) = self._cmd.execute(['rpm-ostree', 'kargs'], return_err=True)
		log.debug("rpm-ostree output stdout:\n%s\nstderr:\n%s" % (out, err))
		if rc != 0:
			return None, None, None
		kargs = self._options_to_dict(out)

		if not self._wait_till_idle():
			log.error("Cannot wait for transaction end")
			return None, None, None

		deleted = {}
		delete_params = self._dict_to_options(delete).split()
		# Deleting kargs, e.g. deleting added kargs by profile
		for k, val in delete.items():
			for v in val:
				kargs[k].remove(v)
			deleted[k] = val

		appended = {}
		append_params = self._dict_to_options(append).split()
		# Appending kargs, e.g. new kargs by profile or restoring kargs replaced by profile
		for k, val in append.items():
			if kargs.get(k):
				# If there is karg that we add with new value we want to delete it
				# and store old value for restoring after profile unload
				log.debug("adding rpm-ostree kargs %s: %s for delete" % (k, kargs[k]))
				deleted.setdefault(k, []).extend(kargs[k])
				delete_params.extend([k + "=" + v if v is not None else k for v in kargs[k]])
				kargs[k] = []
			kargs.setdefault(k, []).extend(val)
			appended[k] = val

		if append_params == delete_params:
			log.info("skipping rpm-ostree kargs - append == deleting (%s)" % append_params)
			return kargs, appended, deleted

		log.info("rpm-ostree kargs - appending: '%s'; deleting: '%s'" % (append_params, delete_params))
		(rc, _, err) = self._cmd.execute(['rpm-ostree', 'kargs'] +
										 ['--append=%s' % v for v in append_params] +
										 ['--delete=%s' % v for v in delete_params], return_err=True)
		if rc != 0:
			log.error("Something went wrong with rpm-ostree kargs\n%s" % (err))
			return self._options_to_dict(out), None, None
		else:
			return kargs, appended, deleted

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
				log.warning("Unknown option '%s' for plugin '%s'." % (key, self.__class__.__name__))
		cmdline = ""
		for key in cmdline_keys:
			val = options[key]
			if val is None or val == "":
				continue
			op = val[0]
			op1 = val[1:2]
			vals = val[1:].strip()
			if op == "+" or (op == "\\" and op1 in ["\\", "+", "-"]):
				if vals != "":
					cmdline += " " + vals
			elif op == "-":
				if vals != "":
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

	def _bls_enabled(self):
		grub2_default_env = self._cmd.read_file(consts.GRUB2_DEFAULT_ENV_FILE, no_error = True)
		if len(grub2_default_env) <= 0:
			log.info("cannot read '%s'" % consts.GRUB2_DEFAULT_ENV_FILE)
			return False

		return re.search(r"^\s*GRUB_ENABLE_BLSCFG\s*=\s*\"?\s*[tT][rR][uU][eE]\s*\"?\s*$", grub2_default_env,
			flags = re.MULTILINE) is not None

	def _patch_bootcmdline(self, d):
		return self._cmd.add_modify_option_in_file(consts.BOOT_CMDLINE_FILE, d)

	def _remove_grub2_tuning(self):
		self._patch_bootcmdline({consts.BOOT_CMDLINE_TUNED_VAR : "", consts.BOOT_CMDLINE_INITRD_ADD_VAR : ""})
		if not self._grub2_cfg_file_names:
			log.info("cannot find grub.cfg to patch")
			return
		for f in self._grub2_cfg_file_names:
			self._cmd.add_modify_option_in_file(f, {r"set\s+" + consts.GRUB2_TUNED_VAR : "", r"set\s+" + consts.GRUB2_TUNED_INITRD_VAR : ""}, add = False)
		if self._initrd_dst_img_val is not None:
			log.info("removing initrd image '%s'" % self._initrd_dst_img_val)
			self._cmd.unlink(self._initrd_dst_img_val)

	def _get_rpm_ostree_changes(self):
		f = self._cmd.read_file(consts.BOOT_CMDLINE_FILE)
		appended = re.search(consts.BOOT_CMDLINE_TUNED_VAR + r"=\"(.*)\"", f, flags=re.MULTILINE)
		appended = appended[1] if appended else ""
		deleted = re.search(consts.BOOT_CMDLINE_KARGS_DELETED_VAR + r"=\"(.*)\"", f, flags=re.MULTILINE)
		deleted = deleted[1] if deleted else ""
		return appended, deleted

	def _remove_rpm_ostree_tuning(self):
		appended, deleted = self._get_rpm_ostree_changes()
		self._rpm_ostree_kargs(append=self._options_to_dict(deleted), delete=self._options_to_dict(appended))
		self._patch_bootcmdline({consts.BOOT_CMDLINE_TUNED_VAR: "", consts.BOOT_CMDLINE_KARGS_DELETED_VAR: ""})

	def _instance_unapply_static(self, instance, rollback = consts.ROLLBACK_SOFT):
		if rollback == consts.ROLLBACK_FULL and not self._skip_grub_config_val:
			if self._rpm_ostree:
				log.info("removing rpm-ostree tuning previously added by Tuned")
				self._remove_rpm_ostree_tuning()
			else:
				log.info("removing grub2 tuning previously added by Tuned")
				self._remove_grub2_tuning()
				self._update_grubenv({"tuned_params" : "", "tuned_initrd" : ""})

	def _grub2_cfg_unpatch(self, grub2_cfg):
		log.debug("unpatching grub.cfg")
		cfg = re.sub(r"^\s*set\s+" + consts.GRUB2_TUNED_VAR + "\\s*=.*\n", "", grub2_cfg, flags = re.MULTILINE)
		grub2_cfg = re.sub(r" *\$" + consts.GRUB2_TUNED_VAR, "", cfg, flags = re.MULTILINE)
		cfg = re.sub(r"^\s*set\s+" + consts.GRUB2_TUNED_INITRD_VAR + "\\s*=.*\n", "", grub2_cfg, flags = re.MULTILINE)
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
			# add TuneD parameters to all kernels
			grub2_cfg = re.sub(r"^(\s*" + i + r"(16|efi)?\s+.*)$", r"\1 $" + d2[i], grub2_cfg, flags = re.MULTILINE)
			# remove TuneD parameters from rescue kernels
			grub2_cfg = re.sub(r"^(\s*" + i + r"(?:16|efi)?\s+\S+rescue.*)\$" + d2[i] + r" *(.*)$", r"\1\2", grub2_cfg, flags = re.MULTILINE)
			# fix whitespaces in rescue kernels
			grub2_cfg = re.sub(r"^(\s*" + i + r"(?:16|efi)?\s+\S+rescue.*) +$", r"\1", grub2_cfg, flags = re.MULTILINE)
		return grub2_cfg

	def _grub2_default_env_patch(self):
		grub2_default_env = self._cmd.read_file(consts.GRUB2_DEFAULT_ENV_FILE)
		if len(grub2_default_env) <= 0:
			log.info("cannot read '%s'" % consts.GRUB2_DEFAULT_ENV_FILE)
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

	def _grub2_default_env_unpatch(self):
		grub2_default_env = self._cmd.read_file(consts.GRUB2_DEFAULT_ENV_FILE)
		if len(grub2_default_env) <= 0:
			log.info("cannot read '%s'" % consts.GRUB2_DEFAULT_ENV_FILE)
			return False

		write = False
		if re.search(r"^GRUB_CMDLINE_LINUX_DEFAULT=\"\$\{GRUB_CMDLINE_LINUX_DEFAULT:\+\$GRUB_CMDLINE_LINUX_DEFAULT \}\\\$" +
			consts.GRUB2_TUNED_VAR + "\"$", grub2_default_env, flags = re.MULTILINE):
				write = True
				cfg = re.sub(r"^GRUB_CMDLINE_LINUX_DEFAULT=\"\$\{GRUB_CMDLINE_LINUX_DEFAULT:\+\$GRUB_CMDLINE_LINUX_DEFAULT \}\\\$" +
					consts.GRUB2_TUNED_VAR + "\"$\n", "", grub2_default_env, flags = re.MULTILINE)
				if cfg[-1] != "\n":
					cfg += "\n"
		if write:
			log.debug("unpatching '%s'" % consts.GRUB2_DEFAULT_ENV_FILE)
			self._cmd.write_to_file(consts.GRUB2_DEFAULT_ENV_FILE, cfg)
		return True

	def _grub2_cfg_patch(self, d):
		log.debug("patching grub.cfg")
		if not self._grub2_cfg_file_names:
			log.info("cannot find grub.cfg to patch")
			return False
		for f in self._grub2_cfg_file_names:
			grub2_cfg = self._cmd.read_file(f)
			if len(grub2_cfg) <= 0:
				log.info("cannot patch %s" % f)
				continue
			log.debug("adding boot command line parameters to '%s'" % f)
			grub2_cfg_new = grub2_cfg
			patch_initial = False
			for opt in d:
				(grub2_cfg_new, nsubs) = re.subn(r"\b(set\s+" + opt + r"\s*=).*$", r"\1" + "\"" + self._cmd.escape(d[opt]) + "\"", grub2_cfg_new, flags = re.MULTILINE)
				if nsubs < 1 or re.search(r"\$" + opt, grub2_cfg, flags = re.MULTILINE) is None:
					patch_initial = True

			# workaround for rhbz#1442117
			if len(re.findall(r"\$" + consts.GRUB2_TUNED_VAR, grub2_cfg, flags = re.MULTILINE)) != \
				len(re.findall(r"\$" + consts.GRUB2_TUNED_INITRD_VAR, grub2_cfg, flags = re.MULTILINE)):
					patch_initial = True

			if patch_initial:
				grub2_cfg_new = self._grub2_cfg_patch_initial(self._grub2_cfg_unpatch(grub2_cfg), d)
			self._cmd.write_to_file(f, grub2_cfg_new)
		if self._bls:
			self._grub2_default_env_unpatch()
		else:
			self._grub2_default_env_patch()
		return True

	def _rpm_ostree_update(self):
		appended, _ = self._get_rpm_ostree_changes()
		_cmdline_dict = self._options_to_dict(self._cmdline_val, appended)
		if not _cmdline_dict:
			return None
		(_, _, d) = self._rpm_ostree_kargs(append=_cmdline_dict)
		if d is None:
			return
		self._patch_bootcmdline({consts.BOOT_CMDLINE_TUNED_VAR : self._cmdline_val, consts.BOOT_CMDLINE_KARGS_DELETED_VAR : self._dict_to_options(d)})

	def _grub2_update(self):
		self._grub2_cfg_patch({consts.GRUB2_TUNED_VAR : self._cmdline_val, consts.GRUB2_TUNED_INITRD_VAR : self._initrd_val})
		self._patch_bootcmdline({consts.BOOT_CMDLINE_TUNED_VAR : self._cmdline_val, consts.BOOT_CMDLINE_INITRD_ADD_VAR : self._initrd_val})

	def _has_bls(self):
		return os.path.exists(consts.BLS_ENTRIES_PATH)

	def _update_grubenv(self, d):
		log.debug("updating grubenv, setting %s" % str(d))
		l = ["%s=%s" % (str(option), str(value)) for option, value in d.items()]
		(rc, out) = self._cmd.execute(["grub2-editenv", "-", "set"] + l)
		if rc != 0:
			log.warning("cannot update grubenv: '%s'" % out)
			return False
		return True

	def _bls_entries_patch_initial(self):
		machine_id = self._cmd.get_machine_id()
		if machine_id == "":
			return False
		log.debug("running kernel update hook '%s' to patch BLS entries" % consts.KERNEL_UPDATE_HOOK_FILE)
		(rc, out) = self._cmd.execute([consts.KERNEL_UPDATE_HOOK_FILE, "add"], env = {"KERNEL_INSTALL_MACHINE_ID" : machine_id})
		if rc != 0:
			log.warning("cannot patch BLS entries: '%s'" % out)
			return False
		return True

	def _bls_update(self):
		log.debug("updating BLS")
		if self._has_bls() and \
			self._update_grubenv({"tuned_params" : self._cmdline_val, "tuned_initrd" : self._initrd_val}) and \
			self._bls_entries_patch_initial():
				return True
		return False

	def _init_initrd_dst_img(self, name):
		if self._initrd_dst_img_val is None:
			self._initrd_dst_img_val = os.path.join(consts.BOOT_DIR, os.path.basename(name))

	def _check_petitboot(self):
		return os.path.isdir(consts.PETITBOOT_DETECT_DIR)

	def _install_initrd(self, img):
		if self._rpm_ostree:
			log.warning("Detected rpm-ostree which doesn't support initrd overlays.")
			return False
		if self._check_petitboot():
			log.warning("Detected Petitboot which doesn't support initrd overlays. The initrd overlay will be ignored by bootloader.")
		log.info("installing initrd image as '%s'" % self._initrd_dst_img_val)
		img_name = os.path.basename(self._initrd_dst_img_val)
		if not self._cmd.copy(img, self._initrd_dst_img_val):
			return False
		self.update_grub2_cfg = True
		curr_cmdline = self._cmd.read_file("/proc/cmdline").rstrip()
		initrd_grubpath = "/"
		lc = len(curr_cmdline)
		if lc:
			path = re.sub(r"^\s*BOOT_IMAGE=\s*(?:\([^)]*\))?(\S*/).*$", "\\1", curr_cmdline)
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
			if self._rpm_ostree:
				rpm_ostree_kargs = self._rpm_ostree_kargs()[0]
				cmdline = self._dict_to_options(rpm_ostree_kargs)
			else:
				cmdline = self._cmd.read_file("/proc/cmdline")
			if len(cmdline) == 0:
				return None
			cmdline_set = set(cmdline.split())
			value_set = set(v.split())
			missing_set = value_set - cmdline_set
			if len(missing_set) == 0:
				log.info(consts.STR_VERIFY_PROFILE_VALUE_OK % ("cmdline", str(value_set)))
				return True
			else:
				cmdline_dict = {v.split("=", 1)[0]: v for v in cmdline_set}
				for m in missing_set:
					arg = m.split("=", 1)[0]
					if not arg in cmdline_dict:
						log.error(consts.STR_VERIFY_PROFILE_CMDLINE_FAIL_MISSING % (arg, m))
					else:
						log.error(consts.STR_VERIFY_PROFILE_CMDLINE_FAIL % (cmdline_dict[arg], m))
				present_set = value_set & cmdline_set
				log.info("expected arguments that are present in cmdline: %s"%(" ".join(present_set),))
				return False
		if enabling and value is not None:
			log.info("installing additional boot command line parameters to grub2")
			self.update_grub2_cfg = True
			self._cmdline_val = v

	@command_custom("skip_grub_config", per_device = False, priority = 10)
	def _skip_grub_config(self, enabling, value, verify, ignore_missing):
		if verify:
			return None
		if enabling and value is not None:
			if self._cmd.get_bool(value) == "1":
				log.info("skipping any modification of grub config")
				self._skip_grub_config_val = True

	def _instance_post_static(self, instance, enabling):
		if enabling and self._skip_grub_config_val:
			if len(self._initrd_val) > 0:
				log.warning("requested changes to initrd will not be applied!")
			if len(self._cmdline_val) > 0:
				log.warning("requested changes to cmdline will not be applied!")
			# ensure that the desired cmdline is always written to BOOT_CMDLINE_FILE (/etc/tuned/bootcmdline)
			self._patch_bootcmdline({consts.BOOT_CMDLINE_TUNED_VAR : self._cmdline_val, consts.BOOT_CMDLINE_INITRD_ADD_VAR : self._initrd_val})
		elif enabling and self.update_grub2_cfg:
			if self._rpm_ostree:
				self._rpm_ostree_update()
			else:
				self._grub2_update()
				self._bls_update()
			self.update_grub2_cfg = False
