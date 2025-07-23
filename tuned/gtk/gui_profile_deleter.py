import os
import sys
import shutil

import tuned.consts

if __name__ == '__main__':

    shutil.rmtree(
        os.path.join(
            tuned.consts.USER_PROFILES_DIR,
            os.path.basename(os.path.abspath(sys.argv[1]))
    ))
