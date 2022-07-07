from . import base
from .decorators import *
import tuned.logs
from tuned.utils.commands import commands
import glob
import socket
import time

log = tuned.logs.get()

class RTENTSKPlugin(base.Plugin):
	"""
	`rtentsk`::
	
	Plugin for avoiding interruptions due to static key IPIs due
        to opening socket with timestamping enabled (by opening a
        socket ourselves the static key is kept enabled).
	"""

	def _instance_init(self, instance):
		instance._has_static_tuning = True
		instance._has_dynamic_tuning = False

		# SO_TIMESTAMP nor SOF_TIMESTAMPING_OPT_TX_SWHW is defined by
		# the socket class

		SO_TIMESTAMP = 29 # see include/uapi/asm-generic/socket.h
		#define SO_TIMESTAMP 0x4012 # parisc!
		SOF_TIMESTAMPING_OPT_TX_SWHW = (1<<14) # see include/uapi/linux/net_tstamp.h

		s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
		s.setsockopt(socket.SOL_SOCKET, SO_TIMESTAMP, SOF_TIMESTAMPING_OPT_TX_SWHW)
		self.rtentsk_socket = s
		log.info("opened SOF_TIMESTAMPING_OPT_TX_SWHW socket")

	def _instance_cleanup(self, instance):
		s = self.rtentsk_socket
		s.close()
