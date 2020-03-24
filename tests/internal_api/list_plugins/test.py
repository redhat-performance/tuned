#!/usr/bin/python

import tuned.plugins
from tuned.plugins.exceptions import NotSupportedPluginException
import tuned.storage

storage_provider = tuned.storage.PickleProvider()
storage_factory = tuned.storage.Factory(storage_provider)
plugins_repo = tuned.plugins.repository.Repository(
	None, None, None, None, None, None, None, None)

names = []
for plugin_class in plugins_repo.load_all_plugins():
	try:
		tmpplg = plugin_class(
			None, storage_factory, None, None, None, None, None, None)
		names.append(tmpplg.name)
	except NotSupportedPluginException:

		class TmpPlgCls(plugin_class):
			"""allows us to bypass problematic plugin_class constructor"""

			def __init__(self, *args, **kwargs):
				super(plugin_class, self).__init__(*args, **kwargs)

		TmpPlgCls.__module__ = plugin_class.__module__
		tmpplg = TmpPlgCls(
			None, storage_factory, None, None, None, None, None, None)
		names.append(tmpplg.name)

# Simple plugin:
assert 'sysctl' in names
# Hotplug plugin:
assert 'disk' in names
# Potentially unsupported plugins:
assert 'bootloader' in names
assert 'selinux' in names
assert 'systemd' in names
assert 'eeepc_she' in names
