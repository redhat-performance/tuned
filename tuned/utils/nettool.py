__all__ = ["ethcard"]

import tuned.logs
from subprocess import *
import re

log = tuned.logs.get()

class Nettool:

	_advertise_values = { # [ half, full ]
		10 : [ 0x001, 0x002 ],
		100 : [ 0x004, 0x008 ],
		1000 : [ 0x010, 0x020 ],
		2500 : [ 0, 0x8000 ], 
		10000 : [ 0, 0x1000 ],
		"auto" : 0x03F
	}

	_disabled = False

	def __init__(self, interface):
		self._interface = interface;
		self.update()

		log.debug("%s: speed %s, full duplex %s, autoneg %s, link %s" % (interface, self.speed, self.full_duplex, self.autoneg, self.link)) 
		log.debug("%s: supports: autoneg %s, modes %s" % (interface, self.supported_autoneg, self.supported_modes))
		log.debug("%s: advertises: autoneg %s, modes %s" % (interface, self.advertised_autoneg, self.advertised_modes))

#	def __del__(self):
#		if self.supported_autoneg:
#			self._set_advertise(self._advertise_values["auto"])

	def _clean_status(self):
		self.speed = 0
		self.full_duplex = False
		self.autoneg = False
		self.link = False

		self.supported_modes = []
		self.supported_autoneg = False

		self.advertised_modes = []
		self.advertised_autoneg = False

	def _calculate_mode(self, modes):
		mode = 0;
		for m in modes:
			mode += self._advertise_values[m[0]][ 1 if m[1] else 0 ]

		return mode

	def _set_autonegotiation(self, enable):
		if self.autoneg == enable:
			return True

		if not self.supported_autoneg:
			return False

		return 0 == call(["ethtool", "-s", self._interface, "autoneg", "on" if enable else "off"], close_fds=True)

	def _set_advertise(self, value):
		if not self._set_autonegotiation(True):
			return False

		return 0 == call(["ethtool", "-s", self._interface, "advertise", "0x%03x" % value], close_fds=True)

	def get_max_speed(self):
		max = 0
		for mode in self.supported_modes:
			if mode[0] > max: max = mode[0]

		if max > 0:
			return max
		else:
			return 1000

	def set_max_speed(self):
		if self._disabled or not self.supported_autoneg:
			return False

		#if self._set_advertise(self._calculateMode(self.supported_modes)):
		if self._set_advertise(self._advertise_values["auto"]):
			self.update()
			return True
		else:
			return False

	def set_speed(self, speed):
		if self._disabled or not self.supported_autoneg:
			return False

		mode = 0
		for am in self._advertise_values:
			if am == "auto": continue
			if am <= speed:
				mode += self._advertise_values[am][0];
				mode += self._advertise_values[am][1];

		effective_mode = mode & self._calculate_mode(self.supported_modes)

		log.debug("%s: set_speed(%d) - effective_mode 0x%03x" % (self._interface, speed, effective_mode))

		if self._set_advertise(effective_mode):
			self.update()
			return True
		else:
			return False

	def update(self):
		if self._disabled:
			return

		# run ethtool and preprocess output

		p_ethtool = Popen(["ethtool", self._interface], \
				stdout=PIPE, stderr=PIPE, close_fds=True, \
				universal_newlines = True)
		p_filter = Popen(["sed", "s/^\s*//;s/:\s*/:\\n/g"], \
				stdin=p_ethtool.stdout, stdout=PIPE, \
				universal_newlines = True, \
				close_fds=True)

		output = p_filter.communicate()[0]
		errors = p_ethtool.communicate()[1]

		if errors != "":
			log.warning("%s: some errors were reported by 'ethtool'" % self._interface)
			log.debug("%s: %s" % (self._interface, errors.replace("\n", r"\n")))
			self._clean_status()
			self._disabled = True
			return

		# parses output - kind of FSM

		self._clean_status()

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
				self.autoneg = (line == "yes" or line == "on")
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
					self.supported_modes.append((1000, True))
	

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
					self.advertised_modes.append((1000, True))

			elif state == "advertised_autoneg":
				self.advertised_autoneg = line == "Yes"
				state = "wait"

def ethcard(interface):
	if not interface in ethcard.list:
		ethcard.list[interface] = Nettool(interface)

	return ethcard.list[interface]

ethcard.list = {}

