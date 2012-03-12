#! /usr/bin/python
#
# Copyright (C) 2012 Red Hat, Inc.
# Authors: Jan Kaluza <jkaluza@redhat.com>
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
#

import os
import sys
import tempfile
import shutil
import argparse
from subprocess import *
from HTMLParser import HTMLParser

KTUNE_SH = """#!/bin/sh

. /etc/tune-profiles/functions

start() {
%s
	return 0
}

stop() {
%s
	return 0
}

process $@
"""


TUNED_CONF = """#
# tuned configuration file
#

[main]
# Interval for monitoring and tuning. Default is 10s.
# interval=10
%s

[powertop_ktune]
merge=1
script=ktune.sh
"""


class PowertopHTMLParser(HTMLParser):
	def __init__(self):
		HTMLParser.__init__(self)

		self.inProperTable = False
		self.lastStartTag = ""
		self.tdCounter = 0
		self.lastDesc = ""
		self.data = ""

	def getParsedData(self):
		return self.data

	def handle_starttag(self, tag, attrs):
		self.lastStartTag = tag
		if self.inProperTable and tag == "td":
			self.tdCounter += 1

	def handle_endtag(self, tag):
		if self.inProperTable and tag == "table":
			self.inProperTable = False
		if tag == "tr":
			self.tdCounter = 0

	def handle_data(self, data):
		if self.lastStartTag == "h2" and data == "Software settings in need of tuning":
			self.inProperTable = True
		if self.inProperTable and self.tdCounter == 1:
			self.lastDesc = data
			if self.lastDesc.lower().find("autosuspend") != -1 and (self.lastDesc.lower().find("keyboard") != -1 or self.lastDesc.lower().find("mouse") != -1):
					self.lastDesc += "\n\t# WARNING: For some devices, uncommenting this command can disable the device."
		if self.inProperTable and self.tdCounter == 2:
			self.tdCounter = 0
			self.data += "\t# " + self.lastDesc + "\n"
			self.data += "\t#" + data + "\n\n"

class PowertopProfile:
	BAD_PRIVS = 100
	PARSING_ERROR = 101
	BAD_KTUNSH = 102

	def __init__(self, output, name = ""):
		self.name = name
		self.output = output

	def currentActiveProfile(self):
		proc = Popen(["tuned-adm", "active"], stdout=PIPE)
		output = proc.communicate()[0]
		if output and output.find("Current active profile: ") == 0:
			return output[len("Current active profile: "):output.find("\n")]
		return "default"

	def checkPrivs(self):
		myuid = os.getuid()
		if myuid != 0:
			print >> sys.stderr, 'Run this program as root'
			return False
		return True

	def generateHTML(self):
		f = tempfile.NamedTemporaryFile()
		name = unicode(f.name)
		f.close()
		
		ret = os.system('powertop --html="%s"' % (name))
		if ret != 0:
			os.unlink(name)
			return ret

		return name;

	def parseHTML(self):
		f = open(self.name)
		parser = PowertopHTMLParser()
		parser.feed(f.read())
		f.close()

		return parser.getParsedData()

	def generateShellScript(self, profile, data):
		if profile == "default" or not os.path.exists(os.path.join(self.output, "ktune.sh")):
			f = open(os.path.join(self.output, "ktune.sh"), "w")
			f.write(KTUNE_SH % (data, ""))
			os.fchmod(f.fileno(), 0755)
			f.close()
		else:
			# Load current ktune.sh
			f = open(os.path.join(self.output, "ktune.sh"), "r")
			script = f.read()
			f.close()

			# Find the start() method
			start = script.find("start()")
			if start != -1:
				# Find its body
				while start < len(script) and script[start] != "{":
					start += 1
				while start < len(script) and script[start] != "\n":
					start += 1

				if start == len(script):
					print >> sys.stderr, 'The start() method does not have a body'

				# Insert our script there
				script = script[:start] + "\n" + data + script[start:]
				f = open(os.path.join(self.output, "ktune.sh"), "w")
				f.write(script)
				f.close()
			else:
				print >> sys.stderr, 'No start() method found in the ktune.sh'
				return False
		return True

	def generateTunedConf(self, profile):
		f = open(os.path.join(self.output, "tuned.conf"), "w")
		f.write(TUNED_CONF % ("include=" + os.path.join("/etc/tune-profiles", profile, "tuned.conf")))
		f.close()

	def copyProfile(self, profile):
		for f in os.listdir(os.path.join("/etc/tune-profiles", profile)):
			shutil.copy(os.path.join("/etc/tune-profiles", profile, f), self.output)

	def generate(self):
		generated_html = False
		if len(self.name) == 0:
			generated_html = True
			if not self.checkPrivs():
				return self.BAD_PRIVS

			name = self.generateHTML()
			if isinstance(name, int):
				return name
			self.name = name

		data = self.parseHTML()

		if generated_html:
			os.unlink(self.name)

		if len(data) == 0:
			print >> sys.stderr, 'Your Powertop version is too old or the generated HTML output is malformed'
			return self.PARSING_ERROR

		profile = self.currentActiveProfile()

		if not os.path.exists(self.output):
			os.makedirs(self.output)

		if profile != "default":
			self.copyProfile(profile)

		if not self.generateShellScript(profile, data):
			return self.BAD_KTUNSH

		self.generateTunedConf(profile)

		return 0

def usage():
	print "Usage:"
	print sys.argv[0] + " <output_directory> [intput_powertop_html_file]"

if __name__ == "__main__":
	parser = argparse.ArgumentParser(description='Creates Tuned profile from Powertop HTML output.')
	parser.add_argument('output', metavar='output_directory', type=unicode, nargs='?', help='Output directory.')
	parser.add_argument('input', metavar='input_html', type=unicode, nargs='?',help='Path to Powertop HTML report. If not given, it is generated automatically.')
	parser.add_argument('--write', metavar='profile_name', type=unicode, help='Name for the profile. If the name is given, the profile is written into /etc/tuned directory.')
	parser.add_argument('--force', action='store_true', help='Overwrites the output directory if it already exists.')
	args = parser.parse_args()
	args = vars(args)

	if args['write']:
		args['output'] = os.path.join("/etc/tune-profiles", args['write'])
	if not args['input']:
		args['input'] = ''

	if not args['output']:
		print >> sys.stderr, 'You have to specify the output directory or the profile name using the --write argument.'
		parser.print_help()
		sys.exit(-1)

	if os.path.exists(args['output']) and not args['force']:
		print >> sys.stderr, 'Output directory already exists, use --force to overwrite it.'
		sys.exit(-1)

	p = PowertopProfile(args['output'], args['input'])
	sys.exit(p.generate())
