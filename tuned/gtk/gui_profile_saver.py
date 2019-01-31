import os
import sys
import json
from configobj import ConfigObj


if __name__ == "__main__":

	profile_dict = json.loads(str(sys.argv[1]))

	if not os.path.exists(profile_dict['filename']):
		os.makedirs(os.path.dirname(profile_dict['filename']))

	profile_configobj = ConfigObj()
	for section in profile_dict['sections']:
		profile_configobj[section] = profile_dict['main'][section]

	profile_configobj.filename = os.path.join('/etc','tuned',os.path.dirname(os.path.abspath(profile_dict['filename'])),'tuned.conf')
	profile_configobj.initial_comment = profile_dict['initial_comment']

	profile_configobj.write()

	sys.exit(0)
