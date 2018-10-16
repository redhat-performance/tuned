import os
import sys
import shutil

if __name__ == '__main__':

	shutil.rmtree('/etc/tuned/%s' % (os.path.basename(os.path.abspath(sys.argv[1]))))
