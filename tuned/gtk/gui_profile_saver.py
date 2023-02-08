import os
import sys
import json
from tuned.utils.config_parser import ConfigParser


if __name__ == "__main__":

	profile_dict = json.loads(str(sys.argv[1]))

	if not os.path.exists(profile_dict['filename']):
		os.makedirs(os.path.dirname(profile_dict['filename']))

	profile_configobj = ConfigParser(delimiters=('='), inline_comment_prefixes=('#'), strict=False)
	profile_configobj.optionxform = str
	for section, options in profile_dict['main'].items():
		profile_configobj.add_section(section)
		for option, value in options.items():
			profile_configobj.set(section, option, value)

	path = os.path.join('/etc','tuned',os.path.dirname(os.path.abspath(profile_dict['filename'])),'tuned.conf')
	with open(path, 'w') as f:
		profile_configobj.write(f)
	with open(path, 'r+') as f:
		content = f.read()
		f.seek(0, 0)
		f.write("\n".join(profile_dict['initial_comment']) + "\n" + content)

	sys.exit(0)
