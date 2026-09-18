import json

import tuned.logs

log = tuned.logs.get()


def has_set_options_for_source(cmd):
	"""Check for a booted deployment and the source-tracking command."""
	(rc, _, _) = cmd.execute(
		['bootc', 'loader-entries', 'set-options-for-source', '--help'],
		return_err=True)
	if rc != 0:
		return False

	# Status can succeed on a package-mode host with no booted deployment.
	(rc, out, _) = cmd.execute(['bootc', 'status', '--json'], return_err=True)
	if rc != 0:
		return False
	try:
		booted = json.loads(out)['status']['booted']
		return isinstance(booted, dict) and bool(booted)
	except (ValueError, KeyError, TypeError):
		log.debug('Cannot determine the booted deployment from bootc status')
		return False
