import os
import re
import pwd, grp

from . import interfaces
import tuned.logs
import tuned.consts as consts
from inspect import ismethod
import socket
import json
import select

log = tuned.logs.get()

class UnixSocketExporter(interfaces.ExporterInterface):
	"""
	Export method calls through Unix Domain Socket Interface.

	We take a method to be exported and create a simple wrapper function
	to call it. This is required as we need the original function to be
	bound to the original object instance. While the wrapper will be bound
	to an object we dynamically construct.
	"""

	def __init__(self, socket_path=consts.CFG_DEF_UNIX_SOCKET_PATH,
				 signal_paths=consts.CFG_DEF_UNIX_SOCKET_SIGNAL_PATHS,
				 ownership=consts.CFG_DEF_UNIX_SOCKET_OWNERSHIP,
				 permissions=consts.CFG_DEF_UNIX_SOCKET_PERMISIONS,
				 connections_backlog=consts.CFG_DEF_UNIX_SOCKET_CONNECTIONS_BACKLOG):

		self._socket_path = socket_path
		self._socket_object = None
		self._socket_signal_paths = signal_paths
		self._socket_signal_objects = []
		self._ownership = [-1, -1]
		if ownership:
			ownership = ownership.split()
			for i, o in enumerate(ownership[:2]):
				try:
					self._ownership[i] = int(o)
				except ValueError:
					try:
						# user
						if i == 0:
							self._ownership[i] = pwd.getpwnam(o).pw_uid
						# group
						else:
							self._ownership[i] = grp.getgrnam(o).gr_gid
					except KeyError:
						log.error("%s '%s' does not exists, leaving default" % ("User" if i == 0 else "Group", o))
		self._permissions = permissions
		self._connections_backlog = connections_backlog

		self._unix_socket_methods = {}
		self._signals = set()
		self._conn = None
		self._channel = None

	def running(self):
		return self._socket_object is not None

	def export(self, method, in_signature, out_signature):
		if not ismethod(method):
			raise Exception("Only bound methods can be exported.")

		method_name = method.__name__
		if method_name in self._unix_socket_methods:
			raise Exception("Method with this name (%s) is already exported." % method_name)

		class wrapper(object):
			def __init__(self, in_signature, out_signature):
				self._in_signature = in_signature
				self._out_signature = out_signature
				
			def __call__(self, *args, **kwargs):
				return method(*args, **kwargs)

		self._unix_socket_methods[method_name] = wrapper(in_signature, out_signature)

	def signal(self, method, out_signature):
		if not ismethod(method):
			raise Exception("Only bound methods can be exported.")
		
		method_name = method.__name__
		if method_name in self._unix_socket_methods:
			raise Exception("Method with this name (%s) is already exported." % method_name)
		
		class wrapper(object):
			def __init__(self, out_signature):
				self._out_signature = out_signature
			
			def __call__(self, *args, **kwargs):
				return method(*args, **kwargs)
		
		self._unix_socket_methods[method_name] = wrapper(out_signature)
		self._signals.add(method_name)

	def send_signal(self, signal, *args, **kwargs):
		if not signal in self._signals:
			raise Exception("Signal '%s' doesn't exist." % signal)
		for p in self._socket_signal_paths:
			log.debug("Sending signal on socket %s" % p)
			try:
				s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
				s.setblocking(False)
				s.connect(p)
				self._send_data(s, {"jsonrpc": "2.0", "method": signal, "params": args})
				s.close()
			except OSError as e:
				log.warning("Error while sending signal '%s' to socket '%s': %s" % (signal, p, e))

	def register_signal_path(self, path):
		self._socket_signal_paths.append(path)

	def _construct_socket_object(self):
		if self._socket_path:
			if os.path.exists(self._socket_path):
				os.unlink(self._socket_path)
			self._socket_object = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
			self._socket_object.bind(self._socket_path)
			self._socket_object.listen(self._connections_backlog)
			os.chown(self._socket_path, self._ownership[0], self._ownership[1])
			if self._permissions:
				os.chmod(self._socket_path, self._permissions)

	def start(self):
		if self.running():
			return

		self.stop()
		self._construct_socket_object()

	def stop(self):
		if self._socket_object:
			self._socket_object.close()

	def _send_data(self, s, data):
		log.debug("Sending socket data: %s)" % data)
		try:
			s.send(json.dumps(data).encode("utf-8"))
		except Exception as e:
			log.warning("Failed to send data '%s': %s" % (data, e))

	def _create_response(self, data, id, error=False):
		res = {
			"jsonrpc": "2.0",
			"id": id
		}
		if error:
			res["error"] = data
		else:
			res["result"] = data
		return res

	def _create_error_responce(self, code, message, id=None, data=None):
		return self._create_response({
			"code": code,
			"message": message,
			"data": data,
		}, error=True, id=id)

	def _create_result_response(self, result, id):
		return self._create_response(result, id)

	def _check_id(self, data):
		if data.get("id"):
			return data
		return None

	def _process_request(self, req):
		if type(req) != dict or req.get("jsonrpc") != "2.0" or not req.get("method"):
			return self._create_error_responce(-32600, "Invalid Request")
		id = req.get("id")
		ret = None
		if req["method"] not in self._unix_socket_methods:
			return self._check_id(self._create_error_responce(-32601, "Method not found", id))
		try:
			if not req.get("params"):
				ret = self._unix_socket_methods[req["method"]]()
			elif type(req["params"]) in (list, tuple):
				ret = self._unix_socket_methods[req["method"]](*req["params"])
			elif type(req["params"]) == dict:
				ret = self._unix_socket_methods[req["method"]](**req["params"])
			else:
				return self._check_id(self._create_error_responce(-32600, "Invalid Request", id))
		except TypeError as e:
			return self._check_id(self._create_error_responce(-32602, "Invalid params", id, str(e)))
		except Exception as e:
			return self._check_id(self._create_error_responce(1, "Error", id, str(e)))
		return self._check_id(self._create_result_response(ret, id))

	def period_check(self):
		"""
		Periodically checks socket object for new calls. This allows to function without special thread.
		Interface is according JSON-RPC 2.0 Specification (see https://www.jsonrpc.org/specification)
		
		Example calls:
		
		printf '[{"jsonrpc": "2.0", "method": "active_profile", "id": 1}, {"jsonrpc": "2.0", "method": "profiles", "id": 2}]' | nc -U /run/tuned/tuned.sock
		printf '{"jsonrpc": "2.0", "method": "switch_profile", "params": {"profile_name": "balanced"}, "id": 1}' | nc -U /run/tuned/tuned.sock
		"""
		if not self.running():
			return
		while True:
			r, _, _ = select.select([self._socket_object], (), (), 0)
			if r:
				conn, _ = self._socket_object.accept()
				try:
					data = ""
					while True:
						rec_data = conn.recv(4096).decode()
						if not rec_data:
							break
						data += rec_data
				except Exception as e:
					log.error("Failed to load data of message: %s" % e)
					continue
				if data:
					try:
						data = json.loads(data)
					except Exception as e:
						log.error("Failed to load json data '%s': %s" % (data, e))
						self._send_data(conn, self._create_error_responce(-32700, "Parse error", str(e)))
						continue
					if type(data) not in (tuple, list, dict):
						log.error("Wrong format of call")
						self._send_data(conn, self._create_error_responce(-32700, "Parse error", str(e)))
						continue
					if type(data) in (tuple, list):
						if len(data) == 0:
							self._send_data(conn, self._create_error_responce(-32600, "Invalid Request", str(e)))
							continue
						res = []
						for req in data:
							r = self._process_request(req)
							if r:
								res.append(r)
						if res:
							self._send_data(conn, res)
					else:
						res = self._process_request(data)
						if r:
							self._send_data(conn, res)
			else:
				return
		
