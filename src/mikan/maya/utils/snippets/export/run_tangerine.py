# coding: utf-8

import os
import mikan
import subprocess

from mikan.core.prefs import UserPrefs

# get tangerine path
path_exe = UserPrefs.get('tangerine_path')
path_exe = os.path.abspath(path_exe)
if not os.path.exists(path_exe):
    raise RuntimeError('invalid path: {}'.format(path_exe))

path_cwd = os.path.split(path_exe)[0]

# update env
mikan_src = os.path.abspath(mikan.__path__[0])
mikan_src = os.path.split(mikan_src)[0]

env = os.environ.copy()
env["TANG_MIKAN_PATH"] = mikan_src
env["MIKAN_MENU"] = "on"

# run tangerine
subprocess.Popen([path_exe], cwd=path_cwd, env=env)
