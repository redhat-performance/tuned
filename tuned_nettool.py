# Copyright (C) 2008, 2009 Red Hat, Inc.
# Authors: Jan Vcelak <jvcelak@redhat.com>
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

from subprocess import *
import re

class Tuned_nettool:

	__advertise_values = { # [ half, full ]
		10 : [ 0x001, 0x002 ],
		100 : [ 0x004, 0x008 ],
		1000 : [ 0x010, 0x020 ],
		2500 : [ 0, 0x8000 ], 
		10000 : [ 0, 0x1000 ],
		"auto" : 0x03F
	}

	def __init__(self, interface):
		self.__interface = interface;
		self.update()

#		print "speed:", self.speed
#		print "full dupl:", self.full_duplex
#		print "autoneg:", self.autoneg
#		print "link:", self.link
#		print "sup modes:", self.supported_modes
#		print "sup autoneg:", self.supported_autoneg
#		print "adv modes:", self.advertised_modes
#		print "adv autoneg:", self.advertised_autoneg

#	def __del__(self):
#		if self.supported_autoneg:
#			self.__set_advertise(self.__advertise_values["auto"])

	def __clean_status(self):
		self.speed = 0
		self.full_duplex = False
		self.autoneg = False
		self.link = False

		self.supported_modes = []
		self.supported_autoneg = False

		self.advertised_modes = []
		self.advertised_autoneg = False

	def __calculate_mode(self, modes):
		mode = 0;
		for m in modes:
			mode += self.__advertise_values[m[0]][ 1 if m[1] else 0 ]

		return mode

	def __set_autonegotiation(self, enable):
		if self.autoneg == enable:
			return True

		if not self.supported_autoneg:
			return False

		return 0 == call(["ethtool", "-s", self.__interface, "autoneg", "on" if enable else "off"])

	def __set_advertise(self, value):
		if not self.__set_autonegotiation(True):
			return False

		return 0 == call(["ethtool", "-s", self.__interface, "advertise", "0x%03x" % value])

	def get_max_speed(self):
		max = 0
		for mode in self.supported_modes:
			if mode[0] > max: max = mode[0]

		if max > 0:
			return max
		else:
			return 1000

	def set_max_speed(self):
		if not self.supported_autoneg:
			return False

		#if self.__set_advertise(self.__calculateMode(self.supported_modes)):
		if self.__set_advertise(self.__advertise_values["auto"]):
			self.update()
			return True
		else:
			return False

	def set_speed(self, speed):
		if not self.supported_autoneg:
			return False

		mode = 0
		for am in self.__advertise_values:
			if am == "auto": continue
			if am <= speed:
				mode += self.__advertise_values[am][0];
				mode += self.__advertise_values[am][1];

		effective_mode = mode & self.__calculate_mode(self.supported_modes)

		if self.__set_advertise(effective_mode):
			self.update()
			return True
		else:
			return False

	def update(self):

		# run ethtool and preprocess output

		p_ethtool = Popen(["ethtool", self.__interface], stdout=PIPE, stderr=PIPE)
		p_filter = Popen(["sed", "s/^\s*//;s/:\s*/:\\n/g"], stdin=p_ethtool.stdout, stdout=PIPE)

		output = p_filter.communicate()[0]
		errors = p_ethtool.communicate()[1]

		if errors != "":
			# it is possible that the network card is not supported
			self.__clean_status()
			return
			# TODO: subject of logging
			#raise Exception("Some errors were reported by 'ethtool'.", errors)

		# parses output - kind of FSM

		self.__clean_status()

		re_speed = re.compile(r"(\d+)")
		re_mode = re.compile(r"(\d+)baseT/(Half|Full)")

		state = "wait"

		for line in output.split("\n"):

			if line.endswith(":"):
				section = line[:-1]
				if section == "Speed": state = "speed"
				elif section == "Duplex": state = "duplex"
				elif section == "Auto-negotiation": state = "autoneg"
				elif section == "Link detected": state = "link"
				elif section == "Supported link modes": state = "supported_modes"
				elif section == "Supports auto-negotiation": state = "supported_autoneg"
				elif section == "Advertised link modes": state = "advertised_modes"
				elif section == "Advertised auto-negotiation": state = "advertised_autoneg"
				else: state = "wait"
				del section

			elif state == "speed":
				# Try to determine speed. If it fails, assume 1gbit ethernet
				try:
					self.speed = re_speed.match(line).group(1)
				except:
					self.speed = 1000
				state = "wait"

			elif state == "duplex":
				self.full_duplex = line == "Full"
				state = "wait"

			elif state == "autoneg":
				self.autoneg = line == "yes"
				state = "wait"

			elif state == "link":
				self.link = line == "yes"
				state = "wait"

			elif state == "supported_modes":
				# Try to determine supported modes. If it fails, assume 1gibt ethernet fullduplex works
				try:
					for m in line.split():
						(s, d) = re_mode.match(m).group(1,2)
						self.supported_modes.append( (int(s), d == "Full") )
					del m,s,d
				except:
					self.supported_modes.append(1000, True)
	

			elif state == "supported_autoneg":
				self.supported_autoneg = line == "Yes"
				state = "wait"

			elif state == "advertised_modes":
				# Try to determine advertised modes. If it fails, assume 1gibt ethernet fullduplex works
				try:
					if line != "Not reported":
						for m in line.split():
							(s, d) = re_mode.match(m).group(1,2)
							self.advertised_modes.append( (int(s), d == "Full") )
						del m,s,d
				except:
					self.advertised_modes.append(1000, True)

			elif state == "advertised_autoneg":
				self.advertised_autoneg = line == "Yes"
				state = "wait"

def ethcard(interface):
	if not interface in ethcard.list:
		#print "ethcard -> Tuned_nettool(%s)" % interface
		ethcard.list[interface] = Tuned_nettool(interface)

	return ethcard.list[interface]

ethcard.list = {}

