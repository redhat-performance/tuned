
import argparse
import os
import inspect
from tuned.utils.class_loader import ClassLoader
from tuned.plugins.base import Plugin


class PluginDocLoader(ClassLoader):
	def __init__(self):
		super(PluginDocLoader, self).__init__()

	def _set_loader_parameters(self):
		self._namespace = "tuned.plugins"
		self._prefix = "plugin_"
		self._interface = Plugin

parser = argparse.ArgumentParser()
parser.add_argument("intro")
parser.add_argument("out")
args = parser.parse_args()

with open(args.intro, "r") as intro_file:
	intro = intro_file.read()

all_plugins = sorted(PluginDocLoader().load_all_classes(), key=lambda x: x.__module__)

with open(args.out, "w") as out_file:
	out_file.write(intro)
	for plugin in all_plugins:
		plugin_file = inspect.getfile(plugin)
		plugin_name = os.path.basename(plugin_file)[7:-3]
		out_file.write("\n")
		out_file.write("== **%s**\n" % plugin_name)
		out_file.write(inspect.cleandoc(plugin.__doc__))
		out_file.write("\n")
